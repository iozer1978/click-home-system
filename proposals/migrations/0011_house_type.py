# Generated migration: HouseType model and house_types M2M on HouseModel

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("proposals", "0010_sync_faq_from_click_home_site"),
    ]

    operations = [
        migrations.CreateModel(
            name="HouseType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80, verbose_name="שם הסוג")),
                ("order", models.IntegerField(default=0, verbose_name="סדר תצוגה")),
                ("slug", models.SlugField(allow_unicode=True, max_length=80, unique=True, verbose_name="מזהה ל־URL")),
            ],
            options={
                "verbose_name": "סוג בית",
                "verbose_name_plural": "סוגי בתים",
                "ordering": ["order", "name"],
            },
        ),
        migrations.AddField(
            model_name="housemodel",
            name="house_types",
            field=models.ManyToManyField(
                blank=True,
                related_name="houses",
                to="proposals.housetype",
                verbose_name="סוגי בית",
            ),
        ),
    ]
