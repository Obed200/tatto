import random

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


def generate_referral_code():
    while True:
        code = f"RIB{random.randint(100000, 999999)}"
        if not Profile.objects.filter(referral_code=code).exists():
            return code


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=160)
    phone_number = models.CharField(max_length=30, unique=True)
    referral_code = models.CharField(max_length=12, unique=True, default=generate_referral_code)
    referred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="referred_users",
    )
    first_referral_bonus_paid = models.BooleanField(default=False)
    welcome_bonus_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name or self.phone_number


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_records(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(
            user=instance,
            defaults={
                "full_name": instance.get_full_name() or instance.username,
                "phone_number": instance.username,
            },
        )
        from transactions.models import Wallet

        Wallet.objects.get_or_create(user=instance)
