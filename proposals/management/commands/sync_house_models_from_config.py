# -*- coding: utf-8 -*-
"""
סנכרון דגמי בתים ותמונות מקובץ התצורה.
מריץ: python manage.py sync_house_models_from_config
"""
import json
import os
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from proposals.models import HouseModel, HouseMedia, HouseType


class Command(BaseCommand):
    help = 'יוצר/מעדכן דגמי בתים ותמונות לפי proposals/data/models_images_config.json'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='הצג רק מה היה קורה בלי ליצור קבצים/רשומות',
        )
        parser.add_argument(
            '--skip-media',
            action='store_true',
            help='עדכן רק רשומות דגמים (כותרות), בלי להעלות תמונות',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        skip_media = options['skip_media']
        base_dir = Path(settings.BASE_DIR)
        config_path = base_dir / 'proposals' / 'data' / 'models_images_config.json'
        catalog_path = base_dir / 'proposals' / 'data' / 'linke_house_catalog_content.json'
        source_dir = base_dir / 'Static' / 'images' / 'House'

        if not config_path.exists():
            self.stderr.write(self.style.ERROR(f'קובץ התצורה לא נמצא: {config_path}'))
            return

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        models_images = config.get('models_images', {})
        model_titles = dict(config.get('model_titles', {}))
        model_content = dict(config.get('model_content', {}))

        # מיזוג קטלוג Linke House אם קיים (כותרות + תוכן + קטגוריות)
        if catalog_path.exists():
            with open(catalog_path, 'r', encoding='utf-8') as f:
                catalog = json.load(f)
            catalog_titles = catalog.get('model_titles', {})
            catalog_content = catalog.get('model_content', {})
            for k, v in catalog_titles.items():
                model_titles[k] = v
            for k, content in catalog_content.items():
                if k not in model_content:
                    model_content[k] = {}
                model_content[k].update(content)

        if dry_run:
            self.stdout.write(self.style.WARNING('מצב dry-run – לא משנים כלום'))

        created = updated = media_ok = media_skip = media_fail = 0

        for config_key, data in models_images.items():
            title = model_titles.get(config_key) or f'דגם {config_key}'
            content = model_content.get(config_key, {})
            description = content.get('description', '')
            specs = content.get('specs', '')
            internal_layout = content.get('internal_layout', '')
            area_sqm = content.get('area_sqm')
            price_estimate = content.get('price_estimate')
            drawings = data.get('drawings', [])
            images = data.get('images', [])

            defaults = {
                'title': title,
                'description': description or '',
                'specs': specs or '',
                'internal_layout': internal_layout or '',
            }
            if area_sqm is not None:
                defaults['area_sqm'] = int(area_sqm)
            if price_estimate is not None:
                defaults['price_estimate'] = int(price_estimate)
            house, was_created = HouseModel.objects.get_or_create(
                config_key=config_key,
                defaults=defaults
            )
            if was_created:
                created += 1
                self.stdout.write(f'  נוצר: {house.title} ({config_key})')
            else:
                changed = False
                if house.title != title:
                    house.title = title
                    changed = True
                if config_key in model_content:
                    c = model_content[config_key]
                    if 'description' in c and house.description != (c.get('description') or ''):
                        house.description = c.get('description') or ''
                        changed = True
                    if 'specs' in c and house.specs != (c.get('specs') or ''):
                        house.specs = c.get('specs') or ''
                        changed = True
                    if 'internal_layout' in c and house.internal_layout != (c.get('internal_layout') or ''):
                        house.internal_layout = c.get('internal_layout') or ''
                        changed = True
                    if 'area_sqm' in c and c.get('area_sqm') is not None:
                        new_area = int(c['area_sqm'])
                        if house.area_sqm != new_area:
                            house.area_sqm = new_area
                            changed = True
                    if 'price_estimate' in c and c.get('price_estimate') is not None:
                        new_price = int(c['price_estimate'])
                        if house.price_estimate != new_price:
                            house.price_estimate = new_price
                            changed = True
                if changed and not dry_run:
                    update_fields = ['title', 'description', 'specs', 'internal_layout']
                    if 'area_sqm' in (model_content.get(config_key) or {}):
                        update_fields.append('area_sqm')
                    if 'price_estimate' in (model_content.get(config_key) or {}):
                        update_fields.append('price_estimate')
                    house.save(update_fields=update_fields)
                    updated += 1
                    self.stdout.write(f'  עודכן: {house.title} ({config_key})')

            # שיוך סוגי בית (house_types) מקטגוריות הקטלוג
            site_categories = content.get('site_categories', [])
            if site_categories and not dry_run:
                types_qs = HouseType.objects.filter(name__in=site_categories)
                current_slugs = set(house.house_types.values_list('slug', flat=True))
                new_slugs = set(types_qs.values_list('slug', flat=True))
                if current_slugs != new_slugs:
                    house.house_types.set(types_qs)
                    self.stdout.write(f'    סוגי בית: {", ".join(types_qs.values_list("name", flat=True))}')
            elif site_categories and dry_run:
                types_qs = HouseType.objects.filter(name__in=site_categories)
                self.stdout.write(f'    [dry-run] סוגי בית: {", ".join(types_qs.values_list("name", flat=True))}')

            if skip_media or dry_run:
                continue

            # שרטוט ראשון -> blueprint_image
            if drawings:
                first_drawing = source_dir / drawings[0]
                if first_drawing.exists():
                    if not house.blueprint_image or not house.blueprint_image.name:
                        with open(first_drawing, 'rb') as f:
                            house.blueprint_image.save(
                                os.path.basename(first_drawing),
                                File(f),
                                save=True
                            )
                        media_ok += 1
                else:
                    self.stdout.write(self.style.WARNING(f'    קובץ חסר: {first_drawing}'))

            # שאר שרטוטים + כל התמונות -> HouseMedia
            other_drawings = drawings[1:] if len(drawings) > 1 else []
            media_order = 0
            for filename in other_drawings + images:
                src = source_dir / filename
                if not src.exists():
                    self.stdout.write(self.style.WARNING(f'    קובץ חסר: {src}'))
                    media_fail += 1
                    continue
                # דילוג אם כבר קיים מדיה עם אותו שם קובץ
                already = any(
                    m.file and (filename in (m.file.name or '') or (m.file.name or '').endswith(filename))
                    for m in house.media_files.all()
                )
                if already:
                    media_skip += 1
                    continue
                with open(src, 'rb') as f:
                    HouseMedia.objects.create(
                        house=house,
                        media_type='image',
                        file=File(f, name=filename),
                        sort_order=media_order * 10,
                        is_homepage_card=(media_order == 0),
                    )
                    media_order += 1
                media_ok += 1

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'סיום: נוצרו {created}, עודכנו {updated}. '
            f'תמונות: {media_ok} הועלו, {media_skip} דולגו (קיימות), {media_fail} חסרים.'
        ))
