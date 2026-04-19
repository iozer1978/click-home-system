# סנכרון דגמי בתים מתמונות (Static/images/House)

## קובץ תצורה
`models_images_config.json` – מגדיר לכל דגם (MODEL_01 … MODEL_34):
- **model_titles** – כותרת בעברית.
- **models_images** – רשימת קבצי תמונות (`images`) ושרטוטים (`drawings`) מתיקיית `Static/images/House`. השרטוט הראשון נשמר כ"שרטוט אדריכלי" (מוצג רק בלשונית שרטוט אדריכלי, לא בגלריית התמונות).
- **model_content** (אופציונלי) – לכל דגם אפשר להוסיף:
  - `description` – תיאור כללי
  - `specs` – מפרט טכני ומידות
  - `internal_layout` – חלוקה פנימית  
  דוגמה: `"MODEL_01": { "description": "טקסט...", "specs": "...", "internal_layout": "..." }`

## קטלוג Linke House (אופציונלי)
`linke_house_catalog_content.json` – אם הקובץ קיים, הפקודה **ממזגת** ממנו:
- **model_titles** – כותרות דגמים (דורס את models_images_config)
- **model_content** – לכל דגם: `description`, `specs`, `internal_layout`, ו־**site_categories** (רשימת שמות קטגוריות בעברית). הקטגוריות ממופות ל־HouseType ושמורות כ־house_types של הדגם.

הרצת הסנכרון אחרי הוספת/עדכון הקטלוג מעדכנת כותרות, תוכן וסוגי בית לדגמים 1–10 (או כל דגם שמופיע בקטלוג).

## הרצת הסנכרון

1. **הרצת מיגרציות** (פעם אחת, אם עדיין לא):
   ```bash
   python manage.py migrate
   ```

2. **וידוא שהתמונות קיימות** בתיקייה:
   `C:\click_home_system\Static\images\House`
   (כל הקבצים שמופיעים ב־JSON צריכים להיות שם.)

3. **הרצת פקודת הסנכרון**:
   ```bash
   python manage.py sync_house_models_from_config
   ```
   - נוצרים/מתעדכנים 34 דגמי בית (HouseModel) עם מזהה סנכרון (config_key) וכותרות עברית.
   - קבצים מ־Static מועתקים ל־media (house_media/, blueprints/) ומקושרים לדגמים.

4. **אפשרויות**:
   - `--dry-run` – רק הצגה, בלי ליצור רשומות או להעלות קבצים.
   - `--skip-media` – עדכון כותרות דגמים בלבד, בלי להעלות תמונות.

## אדמין
בממשק הניהול (דגמי בתים) מופיעים העמודה "מזהה סנכרון" והחיפוש לפי config_key (למשל MODEL_01). ניתן לערוך כותרת, תיאור, סוגי בית ומחיר לכל דגם.
