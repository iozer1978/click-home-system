# Add config_key to HouseModel for sync from models_images_config.json

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("proposals", "0012_add_default_house_types"),
    ]

    operations = [
        migrations.AddField(
            model_name="housemodel",
            name="config_key",
            field=models.CharField(
                blank=True,
                max_length=30,
                null=True,
                unique=True,
                verbose_name="מזהה סנכרון (MODEL_01...)",
            ),
        ),
    ]
