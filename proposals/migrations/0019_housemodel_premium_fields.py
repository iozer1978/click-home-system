from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("proposals", "0018_suppliersubmission"),
    ]

    operations = [
        migrations.AddField(
            model_name="housemodel",
            name="advantages",
            field=models.JSONField(blank=True, default=list, verbose_name="יתרונות הדגם"),
        ),
        migrations.AddField(
            model_name="housemodel",
            name="construction_type",
            field=models.CharField(blank=True, max_length=120, verbose_name="סוג בנייה"),
        ),
        migrations.AddField(
            model_name="housemodel",
            name="delivery_time",
            field=models.CharField(blank=True, max_length=120, verbose_name="זמן אספקה"),
        ),
        migrations.AddField(
            model_name="housemodel",
            name="features",
            field=models.JSONField(blank=True, default=list, verbose_name="פיצ'רים / פס יתרונות"),
        ),
        migrations.AddField(
            model_name="housemodel",
            name="floor_plan_pdf",
            field=models.FileField(blank=True, null=True, upload_to="blueprints/", verbose_name="קובץ שרטוט PDF"),
        ),
        migrations.AddField(
            model_name="housemodel",
            name="full_description",
            field=models.TextField(blank=True, verbose_name="תיאור מלא שיווקי"),
        ),
        migrations.AddField(
            model_name="housemodel",
            name="gallery_images",
            field=models.JSONField(blank=True, default=list, verbose_name="גלריה נוספת (URLs)"),
        ),
        migrations.AddField(
            model_name="housemodel",
            name="hero_image",
            field=models.ImageField(blank=True, null=True, upload_to="house_media/", verbose_name="תמונת Hero"),
        ),
        migrations.AddField(
            model_name="housemodel",
            name="interior_images",
            field=models.JSONField(blank=True, default=list, verbose_name="גלריית פנים (URLs)"),
        ),
        migrations.AddField(
            model_name="housemodel",
            name="related_models",
            field=models.ManyToManyField(blank=True, symmetrical=False, to="proposals.housemodel", verbose_name="דגמים קשורים"),
        ),
        migrations.AddField(
            model_name="housemodel",
            name="short_description",
            field=models.CharField(blank=True, max_length=255, verbose_name="תיאור קצר שיווקי"),
        ),
        migrations.AddField(
            model_name="housemodel",
            name="specifications",
            field=models.JSONField(blank=True, default=dict, verbose_name="מפרט מובנה (JSON)"),
        ),
        migrations.AddField(
            model_name="housemodel",
            name="warranty",
            field=models.CharField(blank=True, max_length=120, verbose_name="אחריות"),
        ),
    ]
