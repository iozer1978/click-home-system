# Tab Catalog Integration (`/tab`)

This document explains how the premium Hebrew RTL catalog page works and how to maintain it.

## Deep Blue data source (internal)

The `/tab` page is now driven primarily by an internal JSON dataset imported from:

- `https://www.deepbluehome.com/singlefamilyhomes`
- `https://www.deepbluehome.com/modularhomes`
- `https://www.deepbluehome.com/adu`

Data file:

- `proposals/data/deepblue_models.json`

Importer script:

- `scripts/import_home_models.py`

Run importer manually when you want to refresh catalog data:

```bash
python scripts/import_home_models.py
```

Important:

- Source references are kept only in `internal_source_reference`.
- Public page content is rendered under Click Home branding only.

## What was added

- Route: `proposals/urls.py` -> `path('tab/', views.tab_page, name='tab')`
- View + filters + lead processing: `proposals/views.py` (`tab_page`)
- Data normalization layer: `proposals/data/home_models.py`
- Template: `proposals/templates/tab.html`
- Template in use: `proposals/templates/tab_v2.html`
- (legacy draft remains: `proposals/templates/tab.html`)
- CSS: `proposals/static/css/tab.css`
- JS: `proposals/static/js/tab.js`
- JS in use: `proposals/static/js/tab_v2.js`
- Local fallback placeholders:
  - `proposals/static/images/tab/placeholders/single-family.svg`
  - `proposals/static/images/tab/placeholders/modular.svg`
  - `proposals/static/images/tab/placeholders/adu.svg`

## Where model data lives

`/tab` uses existing Django DB models (`HouseModel`, `HouseType`, `HouseMedia`) and does **not** scrape live sources.

Normalization happens in:

- `proposals/data/home_models.py`

Main entrypoint:

- `build_tab_catalog(houses)`

Every model is normalized into one dictionary with keys such as:

- `id`, `slug`, `model_name`
- `category`, `category_label_he`
- `short_description_he`, `full_description_he`
- `bedrooms`, `bathrooms`, `floors`, `area_m2`
- `main_image`, `gallery_images`, `floorplan_images`
- `internal_source_reference` (internal only, not rendered)

## Category mapping (for `/tab`)

Categories are normalized into exactly:

- `single-family` -> `בתים פרטיים`
- `modular` -> `בתים מודולריים`
- `adu` -> `ADU`

Mapping is based on `HouseType.slug` in `home_models.py`.  
To tune mapping rules, edit:

- `_MODULAR_SLUGS`
- `_ADU_SLUGS`
- `_SINGLE_FAMILY_SLUGS`

## Images and media

Primary source for images:

- `HouseMedia` records (`media_files`) attached to each `HouseModel`

Main image logic:

- Uses `house.get_main_image()` when available.
- Falls back to category placeholder in:
  - `/static/images/tab/placeholders/<category>.svg`

If you want to use approved local photos for a model:

1. Upload/add the model media through admin (`HouseMedia`) so it appears in `media/`.
2. Ensure one image is selected as homepage/card image (or keep natural order).
3. Optional floor plans can come from `blueprint_image` or media assets.

## How to add/edit models

### Option A (recommended): Django Admin

1. Open admin and edit/create `HouseModel`.
2. Set title, description, area, specs, and internal layout.
3. Attach house types (`HouseType`) for classification.
4. Add media via `HouseMedia`.

### Option B: Existing sync pipeline

If you already use the sync command and config files:

- `proposals/data/models_images_config.json`
- `proposals/data/linke_house_catalog_content.json` (internal use only)

Then run:

```bash
python manage.py sync_house_models_from_config
```

After sync, `/tab` consumes DB data automatically.

## How to add future categories

1. Add new `HouseType` records as needed.
2. Decide if they should appear under existing `/tab` groups (`single-family`, `modular`, `adu`).
3. Update slug sets in `proposals/data/home_models.py`.
4. If you need a brand-new visible chip category, update:
   - `CATEGORY_LABELS` in `home_models.py`
   - `TAB_CATEGORY_OPTIONS` in `views.py`
   - corresponding UI logic in template/JS if required.

## Lead form behavior

- `/tab` form submits `POST` to `tab_page`.
- Server-side validation checks:
  - full name
  - phone
  - optional valid email format
  - interest type
  - message
- On success, server sends email to `info@click-home.co.il` and shows user-facing success message.

The existing `/contact` page was aligned to the same backend validation + send flow.

## Notes for production

- No runtime scraping is used.
- Static assets are normal Django static files.
- Works with PythonAnywhere-friendly deployment model.
- Keep all source-brand references internal only and never in public template/meta/alt text.
