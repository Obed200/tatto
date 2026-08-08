from django.db import migrations


PLANS = [
    ("TATTO LEV 1", 10000, 800, 130),
    ("TATTO LEV 2", 15000, 1200, 130),
    ("TATTO LEV 3", 20000, 1600, 130),
    ("TATTO LEV 4", 30000, 2400, 130),
    ("TATTO LEV 5", 40000, 3400, 120),
    ("TATTO LEV 6", 50000, 4250, 120),
    ("TATTO LEV 7", 70000, 7630, 120),
    ("TATTO LEV 8", 90000, 8100, 100),
    ("TATTO LEV 9", 120000, 12000, 95),
    ("TATTO LEV 10", 150000, 15000, 95),
    ("TATTO LEV 11", 300000, 30000, 95),
    ("TATTO LEV 12", 500000, 50000, 95),
    ("TATTO LEV 13", 700000, 70000, 95),
    ("TATTO LEV 14", 900000, 90000, 95),
]


def update_plans(apps, schema_editor):
    InvestmentPlan = apps.get_model("investments", "InvestmentPlan")
    for index, (name, amount, daily_income, duration_days) in enumerate(PLANS, start=1):
        InvestmentPlan.objects.update_or_create(
            sort_order=index,
            defaults={
                "name": name,
                "amount": amount,
                "daily_income": daily_income,
                "duration_days": duration_days,
                "is_active": True,
            },
        )


def restore_ribural_plans(apps, schema_editor):
    InvestmentPlan = apps.get_model("investments", "InvestmentPlan")
    old_plans = [
        ("Ribural Level 1", 10000, 1500, 20),
        ("Ribural Level 2", 20000, 3000, 20),
        ("Ribural Level 3", 30000, 4500, 20),
        ("Ribural Level 4", 50000, 7500, 20),
        ("Ribural Level 5", 80000, 12000, 20),
        ("Ribural Level 6", 90000, 13500, 20),
        ("Ribural Level 7", 150000, 22000, 20),
        ("Ribural Level 8", 200000, 28000, 20),
        ("Ribural Level 9", 300000, 33000, 20),
        ("Ribural Level 10", 400000, 44000, 20),
        ("Ribural Level 11", 500000, 55000, 20),
        ("Ribural Level 12", 700000, 77000, 20),
        ("Ribural Level 13", 800000, 88000, 20),
        ("Ribural Level 14", 900000, 99000, 20),
    ]
    for index, (name, amount, daily_income, duration_days) in enumerate(old_plans, start=1):
        InvestmentPlan.objects.update_or_create(
            sort_order=index,
            defaults={
                "name": name,
                "amount": amount,
                "daily_income": daily_income,
                "duration_days": duration_days,
                "is_active": True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("investments", "0002_seed_ribural_plans"),
    ]

    operations = [
        migrations.RunPython(update_plans, restore_ribural_plans),
    ]
