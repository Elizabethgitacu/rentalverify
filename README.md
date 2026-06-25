# rentalverify

RentalVerify now has:
- server-rendered pages
- form handling
- session-based login flows
- SQLite-backed storage
- a simple database init runner

## Run locally

```powershell
pip install -r requirements.txt
python -m app.db.migrate
uvicorn app.main:app --reload
```

The SQLite database file is created automatically at `rentalverify.sqlite3`.

## Pages

- `/`
- `/search`
- `/search/result`
- `/report`
- `/report/confirmation`
- `/landlord/register`
- `/landlord/login`
- `/user/login`
- `/landlord/dashboard`
- `/admin/login`
- `/admin/access`
- `/admin/dashboard`
- `/admin/landlords`
- `/admin/reports`
- `/admin/analytics`
- `/404`

