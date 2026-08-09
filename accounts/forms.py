from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Profile
from django.core.exceptions import ValidationError


class RegisterForm(UserCreationForm):
    full_name = forms.CharField(max_length=160)
    phone_number = forms.CharField(max_length=30)
    referral_code = forms.CharField(max_length=12, required=False)

    class Meta:
        model = User
        fields = ["full_name", "phone_number", "password1", "password2", "referral_code"]

    def clean_phone_number(self):
        phone_number = self.cleaned_data["phone_number"].strip()
        if User.objects.filter(username=phone_number).exists() or Profile.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("An account with this phone number already exists.")
        return phone_number

    def clean_referral_code(self):
        code = self.cleaned_data.get("referral_code", "").strip()
        if not code:
            return code
        profile = Profile.objects.filter(referral_code__iexact=code).first()
        if not profile:
            raise forms.ValidationError("Referral code was not found.")
        # Normalize to the exact stored code so save() can match it precisely,
        # regardless of the case the referral link/user typed it in.
        return profile.referral_code

    def save(self, commit=True):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        phone_number = self.cleaned_data["phone_number"]
        user = super().save(commit=False)
        user.username = phone_number
        user.first_name = self.cleaned_data["full_name"]
        if commit:
            user.save()
            profile = user.profile
            profile.full_name = self.cleaned_data["full_name"]
            profile.phone_number = phone_number
            referral_code = self.cleaned_data.get("referral_code")
            if referral_code:
                profile.referred_by = Profile.objects.get(referral_code=referral_code).user
            else:
                # assign to admin (superuser) if no referral provided
                admin_user = User.objects.filter(is_superuser=True).order_by('id').first()
                if admin_user:
                    profile.referred_by = admin_user
            profile.save()
        return user


class PhoneLoginForm(AuthenticationForm):
    username = forms.CharField(label="Phone number")


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["full_name", "phone_number"]

    def clean_phone_number(self):
        phone_number = self.cleaned_data["phone_number"].strip()
        taken = (
            User.objects.filter(username=phone_number).exclude(pk=self.instance.user_id).exists()
            or Profile.objects.filter(phone_number=phone_number).exclude(pk=self.instance.pk).exists()
        )
        if taken:
            raise forms.ValidationError("An account with this phone number already exists.")
        return phone_number

