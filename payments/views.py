from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from investments.models import Investment, InvestmentPlan
from notifications.models import Notification

from .forms import DepositForm, WithdrawalForm
from .models import Deposit, Withdrawal


@login_required
def deposit_create(request):
    active_or_pending = Investment.objects.filter(
        user=request.user,
        status__in=[Investment.PENDING, Investment.ACTIVE],
    ).exists() or Deposit.objects.filter(user=request.user, status=Deposit.PENDING).exists()
    plans = InvestmentPlan.objects.filter(is_active=True)

    # The plan may be chosen from Tatto Investment ("Invest" button) and carried here
    # via ?plan=<id> so the user never has to pick it again.
    plan_id = request.POST.get("plan") or request.GET.get("plan")
    selected_plan = plans.filter(pk=plan_id).first() if plan_id else None

    form = DepositForm(request.POST or None, request.FILES or None, plans=plans)
    if request.method == "POST":
        if active_or_pending:
            messages.error(request, "You already have an active or pending investment.")
        elif form.is_valid():
            deposit = form.save(commit=False)
            deposit.user = request.user
            deposit.amount = deposit.plan.amount
            deposit.save()
            Notification.objects.create(
                user=request.user,
                title="Deposit Submitted",
                message="Your payment screenshot was submitted and is waiting for admin approval.",
            )
            messages.success(request, "Payment proof submitted. Admin will review it shortly.")
            return redirect("dashboard:user_dashboard")
    return render(
        request,
        'payments/deposit_create.html',
        {
            "form": form,
            "plans": plans,
            "selected_plan": selected_plan,
            "payment_code": settings.PAYMENT_CODE,
            "payment_ussd": settings.PAYMENT_USSD,
            "active_or_pending": active_or_pending,
        },
    )


@login_required
def withdrawal_create(request):
    for investment in request.user.investments.filter(status=Investment.ACTIVE):
        investment.credit_due_earnings()
    form = WithdrawalForm(request.POST or None, initial={"phone_number": request.user.profile.phone_number})
    if request.method == "POST" and form.is_valid():
        withdrawal = form.save(commit=False)
        withdrawal.user = request.user
        if withdrawal.amount <= 0:
            form.add_error("amount", "Amount must be greater than zero.")
        elif withdrawal.amount > request.user.wallet.withdrawable_balance:
            form.add_error("amount", "Amount exceeds your withdrawable balance.")
        elif Withdrawal.objects.filter(user=request.user, status=Withdrawal.PENDING).exists():
            messages.error(request, "You already have a pending withdrawal.")
        else:
            withdrawal.save()
            Notification.objects.create(
                user=request.user,
                title="Withdrawal Submitted",
                message="Your withdrawal request is pending admin review.",
            )
            messages.success(request, "Withdrawal request submitted.")
            return redirect("dashboard:user_dashboard")
    return render(request, 'payments/withdrawal_create.html', {"form": form})
