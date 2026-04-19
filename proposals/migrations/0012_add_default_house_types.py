# Data migration: קטגוריות ברירת מחדל לסוגי בתים

from django.db import migrations


DEFAULT_TYPES = [
    ("בתים מודולריים", "modular", 1),
    ("בתי עץ למגורים", "wood", 2),
    ("בתים מוכנים למגורים", "ready", 3),
    ("בתים ניידים", "mobile", 4),
    ("בנייה קלה בישראל", "light-build", 5),
    ("יחידות דיור מוכנות", "housing-units", 6),
    ("בתים טרומיים", "prefab", 7),
    ("בתים גדולים ומשפחתיים", "large-family", 8),
    ("בתים בינוניים וקטנים", "medium-small", 9),
    ("בתים קומפקטיים", "compact", 10),
    ("בתי מכולות (קונטיינרים)", "container", 11),
    ("משרדים ומבני מסחר", "office-commercial", 12),
]


def add_default_house_types(apps, schema_editor):
    HouseType = apps.get_model("proposals", "HouseType")
    if HouseType.objects.exists():
        return
    for name, slug, order in DEFAULT_TYPES:
        HouseType.objects.create(name=name, slug=slug, order=order)


def remove_default_house_types(apps, schema_editor):
    HouseType = apps.get_model("proposals", "HouseType")
    slugs = [s[1] for s in DEFAULT_TYPES]
    HouseType.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("proposals", "0011_house_type"),
    ]

    operations = [
        migrations.RunPython(add_default_house_types, remove_default_house_types),
    ]
