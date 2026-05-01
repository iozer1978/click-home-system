# Click Home - Supplier Qualification System

This project now includes a production-oriented Supplier Qualification System (SSQ) for international suppliers.

## New SSQ Pages

- ` /ssq/` - public supplier qualification wizard (alias: `/supplier-form/`)
- ` /ssq/thank-you/` - post-submission thank-you page (alias: `/supplier-form/thank-you/`)
- ` /admin/login` - SSQ admin login (password-protected session)
- ` /admin/submissions` - SSQ submissions list + filters + CSV export
- ` /admin/submissions/<id>` - SSQ submission detail + notes/status + file access + PDF export

## Core Features Included

- 15-step multi-section supplier evaluation form
- English-first UX with Chinese toggle foundation (`English / 中文`)
- Local autosave in browser storage
- Weighted scoring engine (0-100) with section breakdown
- Critical-risk overrides for missing critical documents/data
- Secure private upload storage (`STORAGE_PATH`)
- Admin summary email + supplier confirmation email
- Admin dashboard with filters, status updates, notes, file links
- CSV export (list) and PDF export (single submission)

## Data Model

Main model: `SupplierSubmission`

Important fields:
- `companyName`, `country`, `contactName`, `email`, `phone`, `website`, `productType`
- `answers` (JSON)
- `files` (JSON)
- `score`, `scoreBreakdown`, `riskLevel`, `criticalFlags`
- `status`, `adminNotes`, `language`
- `createdAt`, `updatedAt`

## Setup

1. Create environment variables:
   - Copy `.env.example` and set real values.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Run migrations:
   - `python manage.py migrate`
4. Start development server:
   - `python manage.py runserver`

## Required Environment Variables

- `DATABASE_URL`
- `SMTP_HOST`
- `SMTP_USER`
- `SMTP_PASS`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`
- `STORAGE_PATH`

## Deployment Notes

- Keep `STORAGE_PATH` outside public static/media folders for secure documents.
- Set a strong `ADMIN_PASSWORD`.
- Set `DJANGO_DEBUG=False` in production.
- Configure real SMTP credentials and sender domain.
- Ensure reverse proxy allows upload size expected by the form.
