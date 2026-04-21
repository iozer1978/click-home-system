import json
from pathlib import Path

from django.core.management.base import BaseCommand

from proposals.models import TabHouse


class Command(BaseCommand):
    help = "סנכרון דגמי /tab מקובץ JSON פנימי לאדמין"

    def handle(self, *args, **options):
        data_path = Path(__file__).resolve().parents[2] / "data" / "deepblue_models.json"
        if not data_path.exists():
            self.stdout.write(self.style.ERROR(f"File not found: {data_path}"))
            return

        payload = json.loads(data_path.read_text(encoding="utf-8"))
        created, updated = 0, 0

        for idx, item in enumerate(payload, start=1):
            house, is_created = TabHouse.objects.update_or_create(
                slug=item.get("slug") or f"tab-house-{idx}",
                defaults={
                    "model_name": item.get("model_name_he") or item.get("model_name") or f"דגם {idx}",
                    "subtitle_he": item.get("subtitle_he", ""),
                    "category": item.get("category") or "single-family",
                    "bedrooms": int(item.get("bedrooms") or 0),
                    "bathrooms": int(item.get("bathrooms") or 0),
                    "living_rooms": int(item.get("living_rooms") or 1),
                    "kitchen_count": int(item.get("kitchen_count") or item.get("kitchens") or 1),
                    "garages": int(item.get("garages") or 0),
                    "floors": int(item.get("floors") or 1),
                    "area_m2": float(item.get("area_m2") or 0),
                    "length_m": item.get("length_m"),
                    "width_m": item.get("width_m"),
                    "description_he": item.get("description_he") or item.get("full_description_he") or "",
                    "features_he": "\n".join(item.get("features_he") or []),
                    "inquiry_cta_label": item.get("inquiry_cta_label") or "אני רוצה פרטים",
                    "is_published": True,
                    "sort_order": idx,
                },
            )
            created += 1 if is_created else 0
            updated += 0 if is_created else 1

        self.stdout.write(self.style.SUCCESS(f"Done. created={created}, updated={updated}, total={len(payload)}"))
