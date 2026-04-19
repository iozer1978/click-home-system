# Data migration: הוספת סוג בית "בנייה קלה ומבנים ניידים"

from django.db import migrations


def add_light_mobile_type(apps, schema_editor):
    HouseType = apps.get_model("proposals", "HouseType")
    if not HouseType.objects.filter(slug="light-mobile").exists():
        HouseType.objects.create(
            name="בנייה קלה ומבנים ניידים",
            slug="light-mobile",
            order=13,
        )


def remove_light_mobile_type(apps, schema_editor):
    HouseType = apps.get_model("proposals", "HouseType")
    HouseType.objects.filter(slug="light-mobile").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("proposals", "0013_house_model_config_key"),
    ]

    operations = [
        migrations.RunPython(add_light_mobile_type, remove_light_mobile_type),
    ]
