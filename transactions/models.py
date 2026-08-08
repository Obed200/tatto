from decimal import Decimal

from django.conf import settings
from django.db import models


class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet")
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    withdrawable_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    referral_bonus = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    daily_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    welcome_bonus = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    updated_at = models.DateTimeField(auto_now=True)

    def credit(self, amount, transaction_type, description=""):
        amount = Decimal(amount)
        self.current_balance += amount
        self.withdrawable_balance += amount
        if transaction_type == Transaction.REFERRAL:
            self.referral_bonus += amount
        if transaction_type == Transaction.EARNING:
            self.daily_earnings += amount
        if transaction_type == Transaction.WELCOME_BONUS:
            self.welcome_bonus += amount
        self.save(update_fields=[
            "current_balance", "withdrawable_balance", "referral_bonus",
            "daily_earnings", "welcome_bonus", "updated_at",
        ])
        return Transaction.objects.create(
            user=self.user,
            transaction_type=transaction_type,
            amount=amount,
            status=Transaction.COMPLETED,
            description=description,
        )

    def debit(self, amount, description=""):
        amount = Decimal(amount)
        self.current_balance -= amount
        self.withdrawable_balance -= amount
        self.save(update_fields=["current_balance", "withdrawable_balance", "updated_at"])
        return Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.WITHDRAWAL,
            amount=amount,
            status=Transaction.COMPLETED,
            description=description,
        )

    def __str__(self):
        return f"{self.user.username} wallet"


class Transaction(models.Model):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    EARNING = "earning"
    REFERRAL = "referral"
    WELCOME_BONUS = "welcome_bonus"

    PENDING = "pending"
    COMPLETED = "completed"
    REJECTED = "rejected"

    TYPE_CHOICES = [
        (DEPOSIT, "Deposit"),
        (WITHDRAWAL, "Withdrawal"),
        (EARNING, "Daily earning"),
        (REFERRAL, "Referral bonus"),
        (WELCOME_BONUS, "Welcome bonus"),
    ]
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (COMPLETED, "Completed"),
        (REJECTED, "Rejected"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} {self.transaction_type} {self.amount}"
