# Discover Tamil Nadu 2026–27 — Django + Tailwind FAM Application

A clean, guided web application based on the supplied **DISCOVER TAMIL NADU 2026–27 International FAM Tour Registration & Expression of Interest Form**.

## UX included
- 13 guided sections instead of one overwhelming long form
- Sticky desktop progress navigator + mobile progress bar
- Conditional follow-up fields for Yes/No questions
- Card-style radio and checkbox selections
- 200-word live counter for the applicant bio
- Repeatable professional-language rows
- Browser-side draft autosave using localStorage
- Supporting material upload
- Declaration, privacy notice and digital confirmation
- Django admin for reviewing applications
- Responsive layout for desktop, tablet and mobile

## Run locally
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations applications
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
Then open `http://127.0.0.1:8000/`.

## Tailwind note
The included template uses the Tailwind browser CDN so the design works immediately without a Node build step. For production, replace the CDN with a compiled Tailwind CSS pipeline (Tailwind CLI/Vite) and collect it through Django static files.

## Production architecture recommendations
- PostgreSQL instead of SQLite
- Object storage (S3-compatible) for supporting uploads
- Server-side draft saving for authenticated/invited applicants
- Email verification and submission acknowledgement
- Virus scanning / file type and size validation on uploads
- Rate limiting + bot protection
- Selection/scoring model separated from the applicant record
- Audit log for application status changes
- CSV/XLSX export and filtering for the Selection Committee
- Explicit retention/deletion policy aligned with the privacy notice
