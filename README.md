# rentalverify

RentalVerify now has:
- server-rendered pages
- public landing page
- shared login/register pages
- role-based dashboards
- SQLite-backed storage
- a simple database init runner

## Run locally

```powershell
pip install -r requirements.txt
python -m app.db.migrate
uvicorn app.main:app --reload
```

The SQLite database file is created automatically at `rentalverify.sqlite3`.

Public auth pages:
- `/login`
- `/register`

Dashboards:
- `/tenant/dashboard`
- `/landlord/dashboard`
- `/admin/dashboard`

## Pages

- `/`
- `/search`
- `/search/result`
- `/report`
- `/report/confirmation`
- `/landlord/register`
- `/landlord/login`
- `/tenant/login`
- `/user/login` (legacy alias)
- `/tenant/dashboard`
- `/user/dashboard` (legacy alias)
- `/landlord/dashboard`
- `/admin/login`
- `/admin/access`
- `/admin/dashboard`
- `/admin/landlords`
- `/admin/reports`
- `/admin/analytics`
- `/404`

