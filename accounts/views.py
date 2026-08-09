from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.urls import reverse

from core.models import SiteSettings

from .forms import PhoneLoginForm, ProfileForm, RegisterForm


def register(request): 
    if request.user.is_authenticated:
        return redirect("dashboard:user_dashboard")
    initial = {}
    ref = request.GET.get('ref') or request.GET.get('referral') or request.GET.get('r')
    if ref:
        initial['referral_code'] = ref.strip()
    form = RegisterForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            # Atomic so a mid-save failure never leaves an orphan user; the
            # unique check in the form is not atomic with the insert, so a
            # double-submit / race can still hit the DB constraint here.
            with transaction.atomic():
                user = form.save()
        except IntegrityError:
            form.add_error("phone_number", "An account with this phone number already exists.")
        else:
            login(request, user)
            messages.success(request, "Welcome to Tatto Mark Investment. Your account is ready.")
            return redirect("dashboard:user_dashboard")
    return render(request, 'accounts/register.html', {"form": form})


class RiburalLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = PhoneLoginForm

    def get_default_redirect_url(self):
        # Staff go straight to the Admin Center; a ?next= still takes priority.
        if self.request.user.is_staff:
            return reverse("dashboard:admin_dashboard")
        return super().get_default_redirect_url()


login_view = RiburalLoginView.as_view()
logout_view = LogoutView.as_view()


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user.profile)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                profile = form.save()
                request.user.username = profile.phone_number
                request.user.first_name = profile.full_name
                request.user.save(update_fields=["username", "first_name"])
        except IntegrityError:
            form.add_error("phone_number", "An account with this phone number already exists.")
        else:
            messages.success(request, "Profile updated.")
            return redirect("accounts:profile")
    return render(request, 'accounts/profile.html', {"form": form, "site_settings": SiteSettings.load()})
