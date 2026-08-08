from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Deposit(models.Model):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="deposits")
    plan = models.ForeignKey("investments.InvestmentPlan", on_delete=models.PROTECT, related_name="deposits")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    proof = models.ImageField(upload_to="payment_proofs/")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    admin_note = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def approve(self):
        if self.status == self.APPROVED:
            return
        from investments.models import Investment
        from notifications.models import Notification
        from transactions.models import Transaction

        if Investment.objects.filter(user=self.user, status=Investment.ACTIVE).exists():
            self.reject("User already has an active investment.")
            return

        self.status = self.APPROVED
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_at"])
        investment = Investment.objects.create(
            user=self.user,
            plan=self.plan,
            amount=self.plan.amount,
            daily_income=self.plan.daily_income,
            duration_days=self.plan.duration_days,
        )
        investment.activate()
        Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.DEPOSIT,
            amount=self.amount,
            status=Transaction.COMPLETED,
            description=f"Approved deposit for {self.plan.name}",
        )
        self._pay_welcome_bonus()
        self._pay_referral_bonus()
        Notification.objects.create(
            user=self.user,
            title="Deposit Approved",
            message=f"Your payment for {self.plan.name} was approved and your investment is active.",
        )

    def reject(self, note=""):
        if self.status != self.PENDING:
            return
        from notifications.models import Notification
        from transactions.models import Transaction

        self.status = self.REJECTED
        self.admin_note = note
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "admin_note", "reviewed_at"])
        Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.DEPOSIT,
            amount=self.amount,
            status=Transaction.REJECTED,
            description=note or f"Rejected deposit for {self.plan.name}",
        )
        Notification.objects.create(
            user=self.user,
            title="Deposit Rejected",
            message=note or "Your payment proof was rejected. Please contact support.",
        )

    def _pay_welcome_bonus(self):
        profile = self.user.profile
        if profile.welcome_bonus_paid:
            return
        from django.conf import settings
        from notifications.models import Notification
        from transactions.models import Transaction

        amount = settings.WELCOME_BONUS_AMOUNT
        self.user.wallet.credit(amount, Transaction.WELCOME_BONUS, "One-time welcome bonus")
        profile.welcome_bonus_paid = True
        profile.save(update_fields=["welcome_bonus_paid"])
        Notification.objects.create(
            user=self.user,
            title="Welcome Bonus Received",
            message=f"You received a {amount:,.0f} RWF welcome bonus, added to your balance.",
        )

    def _pay_referral_bonus(self):
        profile = self.user.profile
        if profile.first_referral_bonus_paid or not profile.referred_by:
            return
        from notifications.models import Notification
        from transactions.models import Transaction

        bonus = (self.amount * Decimal("0.10")).quantize(Decimal("0.01"))
        profile.referred_by.wallet.credit(bonus, Transaction.REFERRAL, f"10% referral bonus from {self.user.username}")
        profile.first_referral_bonus_paid = True
        profile.save(update_fields=["first_referral_bonus_paid"])
        Notification.objects.create(
            user=profile.referred_by,
            title="Referral Bonus Received",
            message=f"You received {bonus:,.0f} RWF from {self.user.profile.full_name}'s first investment.",
        )

    def __str__(self):
        return f"{self.user.username} - {self.plan.name} - {self.status}"


class Withdrawal(models.Model):
    PENDING = "pending"
    PAID = "paid"
    REJECTED = "rejected"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (PAID, "Paid"),
        (REJECTED, "Rejected"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="withdrawals")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    phone_number = models.CharField(max_length=30)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    admin_note = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def approve(self):
        if self.status == self.PAID:
            return
        from notifications.models import Notification

        self.user.wallet.debit(self.amount, "Approved withdrawal")
        self.status = self.PAID
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_at"])
        Notification.objects.create(
            user=self.user,
            title="Withdrawal Paid",
            message=f"Your withdrawal of {self.amount:,.0f} RWF was approved.",
        )

    def reject(self, note=""):
        if self.status != self.PENDING:
            return
        from notifications.models import Notification

        self.status = self.REJECTED
        self.admin_note = note
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "admin_note", "reviewed_at"])
        Notification.objects.create(
            user=self.user,
            title="Withdrawal Rejected",
            message=note or "Your withdrawal request was rejected. Please contact support.",
        )

    def __str__(self):
        return f"{self.user.username} withdrawal {self.amount}"
