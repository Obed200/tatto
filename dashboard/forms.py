from django import forms
from django.contrib.auth.models import User

from accounts.models import Profile
from core.models import Announcement, SiteSettings
from investments.models import Investment, InvestmentPlan


class UserAdminForm(forms.Form):
    full_name = forms.CharField(max_length=160)
    phone_number = forms.CharField(max_length=30)
    email = forms.EmailField(required=False)
    current_balance = forms.DecimalField(max_digits=12, decimal_places=2)
    withdrawable_balance = forms.DecimalField(max_digits=12, decimal_places=2)
    referral_bonus = forms.DecimalField(max_digits=12, decimal_places=2)
    daily_earnings = forms.DecimalField(max_digits=12, decimal_places=2)
    welcome_bonus = forms.DecimalField(max_digits=12, decimal_places=2)

    def __init__(self, *args, account=None, **kwargs):
        self.account = account
        super().__init__(*args, **kwargs)

    def clean_phone_number(self):
        phone = self.cleaned_data["phone_number"].strip()
        clashes_user = User.objects.filter(username=phone).exclude(pk=self.account.pk).exists()
        clashes_profile = Profile.objects.filter(phone_number=phone).exclude(pk=self.account.profile.pk).exists()
        if clashes_user or clashes_profile:
            raise forms.ValidationError("Another account already uses this phone number.")
        return phone


class InvestmentPlanForm(forms.ModelForm):
    class Meta:
        model = InvestmentPlan
        fields = ["name", "amount", "daily_income", "duration_days", "is_active", "sort_order"]


class InvestmentForm(forms.ModelForm):
    class Meta:
        model = Investment
        fields = ["plan", "amount", "daily_income", "duration_days", "status", "start_date", "end_date"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ["title", "message", "is_active"]
        widgets = {"message": forms.Textarea(attrs={"rows": 4})}


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = ["whatsapp_community_link", "telegram_community_link", "contact_phone", "support_email"]
