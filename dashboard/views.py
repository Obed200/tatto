from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import Profile
from core.models import Announcement, SiteSettings
from investments.models import Investment, InvestmentPlan
from payments.models import Deposit, Withdrawal
from transactions.models import Transaction

from .forms import AnnouncementForm, InvestmentForm, InvestmentPlanForm, SiteSettingsForm, UserAdminForm


@login_required
def user_dashboard(request):
    for investment in request.user.investments.filter(status=Investment.ACTIVE):
        investment.credit_due_earnings()
    today = timezone.localdate()
    context = {
        "wallet": request.user.wallet,
        "todays_earnings": request.user.transactions.filter(
            transaction_type=Transaction.EARNING,
            created_at__date=today,
        ).aggregate(total=Sum("amount"))["total"] or 0,
        "active_investment": request.user.investments.filter(status=Investment.ACTIVE).first(),
        "pending_deposit": request.user.deposits.filter(status=Deposit.PENDING).first(),
        "pending_withdrawal": request.user.withdrawals.filter(status=Withdrawal.PENDING).first(),
        "transactions": request.user.transactions.all()[:8],
        "notifications": request.user.notifications.all()[:5],
        "announcements": Announcement.objects.filter(is_active=True)[:3],
        "referral_count": Profile.objects.filter(referred_by=request.user).count(),
        "site_settings": SiteSettings.load(),
    }
    return render(request, 'dashboard/user_dashboard.html', context)


@staff_member_required
def admin_dashboard(request):
    today = timezone.localdate()
    for investment in Investment.objects.filter(status=Investment.ACTIVE):
        investment.credit_due_earnings()
    context = {
        "total_users": Profile.objects.count(),
        "total_deposits": Deposit.objects.filter(status=Deposit.APPROVED).aggregate(total=Sum("amount"))["total"] or 0,
        "total_withdrawals": Withdrawal.objects.filter(status=Withdrawal.PAID).aggregate(total=Sum("amount"))["total"] or 0,
        "total_investments": Investment.objects.count(),
        "active_investments": Investment.objects.filter(status=Investment.ACTIVE).count(),
        "todays_earnings": Transaction.objects.filter(transaction_type=Transaction.EARNING, created_at__date=today).aggregate(total=Sum("amount"))["total"] or 0,
        "pending_deposits_count": Deposit.objects.filter(status=Deposit.PENDING).count(),
        "pending_withdrawals_count": Withdrawal.objects.filter(status=Withdrawal.PENDING).count(),
        "referral_bonuses": Transaction.objects.filter(transaction_type=Transaction.REFERRAL).aggregate(total=Sum("amount"))["total"] or 0,
        # Queues the admin acts on directly from this page
        "pending_deposit_list": Deposit.objects.filter(status=Deposit.PENDING).select_related("user", "user__profile", "plan"),
        "pending_withdrawal_list": Withdrawal.objects.filter(status=Withdrawal.PENDING).select_related("user", "user__profile"),
        "recent_users": Profile.objects.select_related("user").order_by("-created_at")[:8],
        "recent_transactions": Transaction.objects.select_related("user")[:10],
        "active_plans": InvestmentPlan.objects.filter(is_active=True),
        "section": "overview",
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


def _back(request, fallback="dashboard:admin_dashboard"):
    """Return to the page the action was triggered from (dashboard or user page)."""
    return redirect(request.META.get("HTTP_REFERER") or fallback)


@staff_member_required
@require_POST
def approve_deposit(request, pk):
    deposit = get_object_or_404(Deposit, pk=pk)
    if deposit.status != Deposit.PENDING:
        messages.warning(request, "That deposit was already reviewed.")
        return _back(request)

    # Plan correction: the user may have selected one plan but paid for a
    # cheaper/different one. The admin can switch the plan here instead of
    # rejecting, so the activated investment matches what was actually paid.
    plan_id = request.POST.get("plan")
    if plan_id and str(deposit.plan_id) != str(plan_id):
        new_plan = InvestmentPlan.objects.filter(pk=plan_id, is_active=True).first()
        if new_plan:
            old_name = deposit.plan.name
            deposit.plan = new_plan
            deposit.amount = new_plan.amount
            deposit.save(update_fields=["plan", "amount"])
            messages.info(request, f"Plan changed from {old_name} to {new_plan.name} before approval.")

    deposit.approve()
    if deposit.status == Deposit.APPROVED:
        messages.success(
            request,
            f"Approved {deposit.user.username}'s payment. Investment in {deposit.plan.name} is now active.",
        )
    else:
        messages.warning(request, f"Could not approve: {deposit.admin_note}")
    return _back(request)


@staff_member_required
@require_POST
def reject_deposit(request, pk):
    deposit = get_object_or_404(Deposit, pk=pk)
    note = request.POST.get("note", "").strip() or "Rejected by administrator."
    if deposit.status != Deposit.PENDING:
        messages.warning(request, "That deposit was already reviewed.")
    else:
        deposit.reject(note)
        messages.error(request, f"Rejected {deposit.user.username}'s payment.")
    return _back(request)


@staff_member_required
@require_POST
def approve_withdrawal(request, pk):
    withdrawal = get_object_or_404(Withdrawal, pk=pk)
    if withdrawal.status != Withdrawal.PENDING:
        messages.warning(request, "That withdrawal was already reviewed.")
    else:
        withdrawal.approve()
        messages.success(request, f"Marked {withdrawal.user.username}'s withdrawal as paid.")
    return _back(request)


@staff_member_required
@require_POST
def reject_withdrawal(request, pk):
    withdrawal = get_object_or_404(Withdrawal, pk=pk)
    note = request.POST.get("note", "").strip() or "Rejected by administrator."
    if withdrawal.status != Withdrawal.PENDING:
        messages.warning(request, "That withdrawal was already reviewed.")
    else:
        withdrawal.reject(note)
        messages.error(request, f"Rejected {withdrawal.user.username}'s withdrawal.")
    return _back(request)


# ==========================================================================
# Management pages (in-dashboard CRUD, replacing the Django admin screens)
# ==========================================================================

# -------- Users --------
@staff_member_required
def manage_users(request):
    users = User.objects.select_related("profile", "wallet").order_by("-date_joined")
    q = request.GET.get("q", "").strip()
    role = request.GET.get("role", "")
    if q:
        users = users.filter(
            Q(username__icontains=q)
            | Q(profile__full_name__icontains=q)
            | Q(profile__phone_number__icontains=q)
            | Q(profile__referral_code__icontains=q)
        )
    if role == "admin":
        users = users.filter(is_staff=True)
    elif role == "suspended":
        users = users.filter(is_active=False)
    page = Paginator(users, 25).get_page(request.GET.get("page"))
    return render(request, "dashboard/manage/users.html", {
        "page_obj": page, "section": "users", "q": q, "role": role,
    })


@staff_member_required
def user_detail(request, pk):
    account = get_object_or_404(User.objects.select_related("profile", "wallet"), pk=pk)
    # keep balances/earnings current before showing them
    for inv in account.investments.filter(status=Investment.ACTIVE):
        inv.credit_due_earnings()
    today = timezone.localdate()
    total_earned = account.transactions.filter(transaction_type=Transaction.EARNING).aggregate(t=Sum("amount"))["t"] or 0
    todays_earnings = account.transactions.filter(
        transaction_type=Transaction.EARNING, created_at__date=today
    ).aggregate(t=Sum("amount"))["t"] or 0
    total_withdrawn = account.withdrawals.filter(status=Withdrawal.PAID).aggregate(t=Sum("amount"))["t"] or 0
    total_deposited = account.deposits.filter(status=Deposit.APPROVED).aggregate(t=Sum("amount"))["t"] or 0
    return render(request, "dashboard/manage/user_detail.html", {
        "account": account, "section": "users",
        "deposits": account.deposits.select_related("plan").all()[:30],
        "withdrawals": account.withdrawals.all()[:30],
        "investments": account.investments.select_related("plan").all()[:30],
        "transactions": account.transactions.all()[:40],
        "referrals": Profile.objects.filter(referred_by=account).select_related("user"),
        "total_earned": total_earned,
        "todays_earnings": todays_earnings,
        "total_withdrawn": total_withdrawn,
        "total_deposited": total_deposited,
        "active_plans": InvestmentPlan.objects.filter(is_active=True),
    })


@staff_member_required
def user_edit(request, pk):
    account = get_object_or_404(User.objects.select_related("profile", "wallet"), pk=pk)
    wallet = account.wallet
    initial = {
        "full_name": account.profile.full_name,
        "phone_number": account.profile.phone_number,
        "email": account.email,
        "current_balance": wallet.current_balance,
        "withdrawable_balance": wallet.withdrawable_balance,
        "referral_bonus": wallet.referral_bonus,
        "daily_earnings": wallet.daily_earnings,
        "welcome_bonus": wallet.welcome_bonus,
    }
    form = UserAdminForm(request.POST or None, account=account, initial=initial)
    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data
        try:
            with transaction.atomic():
                profile = account.profile
                profile.full_name = cd["full_name"]
                profile.phone_number = cd["phone_number"]
                profile.save(update_fields=["full_name", "phone_number"])
                account.username = cd["phone_number"]
                account.first_name = cd["full_name"]
                account.email = cd["email"]
                account.save(update_fields=["username", "first_name", "email"])
                wallet.current_balance = cd["current_balance"]
                wallet.withdrawable_balance = cd["withdrawable_balance"]
                wallet.referral_bonus = cd["referral_bonus"]
                wallet.daily_earnings = cd["daily_earnings"]
                wallet.welcome_bonus = cd["welcome_bonus"]
                wallet.save(update_fields=[
                    "current_balance", "withdrawable_balance", "referral_bonus",
                    "daily_earnings", "welcome_bonus",
                ])
        except IntegrityError:
            form.add_error("phone_number", "Another account already uses this phone number.")
        else:
            messages.success(request, f"{account.username}'s account was updated.")
            return redirect("dashboard:user_detail", pk=account.pk)
    return render(request, "dashboard/manage/form.html", {
        "form": form, "section": "users",
        "title": f"Edit {account.profile.full_name or account.username}",
        "back_url": "dashboard:manage_users",
    })


def _guard_user_action(request, account):
    """Return an error message if the acting admin may not modify this account."""
    if account == request.user:
        return "You cannot change your own account here."
    if account.is_superuser:
        return "Superuser accounts cannot be changed from this page."
    return None


@staff_member_required
@require_POST
def user_toggle_active(request, pk):
    account = get_object_or_404(User, pk=pk)
    error = _guard_user_action(request, account)
    if error:
        messages.error(request, error)
    else:
        account.is_active = not account.is_active
        account.save(update_fields=["is_active"])
        messages.success(request, f"{account.username} is now {'active' if account.is_active else 'suspended'}.")
    return redirect(request.META.get("HTTP_REFERER") or "dashboard:manage_users")


@staff_member_required
@require_POST
def user_toggle_staff(request, pk):
    account = get_object_or_404(User, pk=pk)
    error = _guard_user_action(request, account)
    if error:
        messages.error(request, error)
    else:
        account.is_staff = not account.is_staff
        account.save(update_fields=["is_staff"])
        messages.success(request, f"{account.username} is now {'an admin' if account.is_staff else 'a regular user'}.")
    return redirect(request.META.get("HTTP_REFERER") or "dashboard:manage_users")


# -------- Investment plans --------
@staff_member_required
def manage_plans(request):
    plans = InvestmentPlan.objects.all()
    return render(request, "dashboard/manage/plans.html", {"plans": plans, "section": "plans"})


@staff_member_required
def plan_create(request):
    form = InvestmentPlanForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        plan = form.save()
        messages.success(request, f"Plan '{plan.name}' created.")
        return redirect("dashboard:manage_plans")
    return render(request, "dashboard/manage/form.html", {
        "form": form, "section": "plans", "title": "New investment plan",
        "back_url": "dashboard:manage_plans",
    })


@staff_member_required
def plan_edit(request, pk):
    plan = get_object_or_404(InvestmentPlan, pk=pk)
    form = InvestmentPlanForm(request.POST or None, instance=plan)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Plan '{plan.name}' updated.")
        return redirect("dashboard:manage_plans")
    return render(request, "dashboard/manage/form.html", {
        "form": form, "section": "plans", "title": f"Edit {plan.name}",
        "back_url": "dashboard:manage_plans", "delete_url": "dashboard:plan_delete", "object": plan,
    })


@staff_member_required
@require_POST
def plan_delete(request, pk):
    plan = get_object_or_404(InvestmentPlan, pk=pk)
    if plan.investments.exists() or plan.deposits.exists():
        messages.error(request, f"Cannot delete '{plan.name}' — it has investments or deposits. Deactivate it instead.")
    else:
        name = plan.name
        plan.delete()
        messages.success(request, f"Plan '{name}' deleted.")
    return redirect("dashboard:manage_plans")


@staff_member_required
@require_POST
def plan_toggle(request, pk):
    plan = get_object_or_404(InvestmentPlan, pk=pk)
    plan.is_active = not plan.is_active
    plan.save(update_fields=["is_active"])
    messages.success(request, f"Plan '{plan.name}' is now {'active' if plan.is_active else 'inactive'}.")
    return redirect("dashboard:manage_plans")


# -------- Investments --------
@staff_member_required
def manage_investments(request):
    investments = Investment.objects.select_related("user", "plan").all()
    status = request.GET.get("status", "")
    q = request.GET.get("q", "").strip()
    if status:
        investments = investments.filter(status=status)
    if q:
        investments = investments.filter(
            Q(user__username__icontains=q) | Q(user__profile__full_name__icontains=q) | Q(plan__name__icontains=q)
        )
    page = Paginator(investments, 25).get_page(request.GET.get("page"))
    return render(request, "dashboard/manage/investments.html", {
        "page_obj": page, "section": "investments",
        "status": status, "q": q, "status_choices": Investment.STATUS_CHOICES,
    })


@staff_member_required
def investment_edit(request, pk):
    investment = get_object_or_404(Investment.objects.select_related("user", "plan"), pk=pk)
    form = InvestmentForm(request.POST or None, instance=investment)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Investment for {investment.user.username} updated. The user's dashboard now reflects the change.")
        return redirect("dashboard:manage_investments")
    who = investment.user.profile.full_name or investment.user.username
    return render(request, "dashboard/manage/form.html", {
        "form": form, "section": "investments",
        "title": f"Edit investment — {who}",
        "back_url": "dashboard:manage_investments",
    })


@staff_member_required
@require_POST
def investment_credit(request, pk):
    investment = get_object_or_404(Investment, pk=pk)
    days = investment.credit_due_earnings()
    messages.success(request, f"Credited {days} day(s) of earnings for {investment.user.username}.")
    return redirect(request.META.get("HTTP_REFERER") or "dashboard:manage_investments")


@staff_member_required
@require_POST
def investment_cancel(request, pk):
    investment = get_object_or_404(Investment, pk=pk)
    investment.status = Investment.CANCELLED
    investment.save(update_fields=["status"])
    messages.warning(request, f"Investment for {investment.user.username} cancelled.")
    return redirect(request.META.get("HTTP_REFERER") or "dashboard:manage_investments")


# -------- Transactions --------
@staff_member_required
def manage_transactions(request):
    txns = Transaction.objects.select_related("user").all()
    ttype = request.GET.get("type", "")
    status = request.GET.get("status", "")
    q = request.GET.get("q", "").strip()
    if ttype:
        txns = txns.filter(transaction_type=ttype)
    if status:
        txns = txns.filter(status=status)
    if q:
        txns = txns.filter(
            Q(user__username__icontains=q) | Q(user__profile__full_name__icontains=q) | Q(description__icontains=q)
        )
    page = Paginator(txns, 30).get_page(request.GET.get("page"))
    return render(request, "dashboard/manage/transactions.html", {
        "page_obj": page, "section": "transactions",
        "type": ttype, "status": status, "q": q,
        "type_choices": Transaction.TYPE_CHOICES, "status_choices": Transaction.STATUS_CHOICES,
    })


# -------- Community links (singleton) --------
@staff_member_required
def manage_community(request):
    settings_obj = SiteSettings.load()
    form = SiteSettingsForm(request.POST or None, instance=settings_obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Community links updated.")
        return redirect("dashboard:manage_community")
    return render(request, "dashboard/manage/form.html", {
        "form": form, "section": "community", "title": "Community & contact links",
        "back_url": "dashboard:admin_dashboard",
    })


# -------- Announcements --------
@staff_member_required
def manage_announcements(request):
    announcements = Announcement.objects.all()
    return render(request, "dashboard/manage/announcements.html", {
        "announcements": announcements, "section": "announcements",
    })


@staff_member_required
def announcement_create(request):
    form = AnnouncementForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Announcement published.")
        return redirect("dashboard:manage_announcements")
    return render(request, "dashboard/manage/form.html", {
        "form": form, "section": "announcements", "title": "New announcement",
        "back_url": "dashboard:manage_announcements",
    })


@staff_member_required
def announcement_edit(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    form = AnnouncementForm(request.POST or None, instance=announcement)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Announcement updated.")
        return redirect("dashboard:manage_announcements")
    return render(request, "dashboard/manage/form.html", {
        "form": form, "section": "announcements", "title": f"Edit: {announcement.title}",
        "back_url": "dashboard:manage_announcements", "delete_url": "dashboard:announcement_delete",
        "object": announcement,
    })


@staff_member_required
@require_POST
def announcement_delete(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    announcement.delete()
    messages.success(request, "Announcement deleted.")
    return redirect("dashboard:manage_announcements")


@staff_member_required
@require_POST
def announcement_toggle(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    announcement.is_active = not announcement.is_active
    announcement.save(update_fields=["is_active"])
    messages.success(request, f"Announcement is now {'active' if announcement.is_active else 'hidden'}.")
    return redirect("dashboard:manage_announcements")
