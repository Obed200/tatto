import re

from django.db import migrations

OLD_PREFIX = "RIB"
NEW_PREFIX = "Tatto"


def rename_prefix(apps, schema_editor):
    Profile = apps.get_model("accounts", "Profile")
    for profile in Profile.objects.filter(referral_code__startswith=OLD_PREFIX):
        suffix = re.sub(r"^" + OLD_PREFIX, "", profile.referral_code)
        profile.referral_code = f"{NEW_PREFIX}{suffix}"
        profile.save(update_fields=["referral_code"])


def restore_prefix(apps, schema_editor):
    Profile = apps.get_model("accounts", "Profile")
    for profile in Profile.objects.filter(referral_code__startswith=NEW_PREFIX):
        suffix = re.sub(r"^" + NEW_PREFIX, "", profile.referral_code)
        profile.referral_code = f"{OLD_PREFIX}{suffix}"
        profile.save(update_fields=["referral_code"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_profile_welcome_bonus_paid_alter_profile_id"),
    ]

    operations = [
        migrations.RunPython(rename_prefix, restore_prefix),
    ]
