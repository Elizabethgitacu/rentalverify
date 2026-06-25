# rentalverify

RentalVerify now has:
- server-rendered pages
- form handling
- session-based login flows
- raw PostgreSQL schema files
- a simple SQL migration runner

## Run locally

```powershell
pip install -r requirements.txt
uvicorn app.main:app --reload
```

If you are using PostgreSQL, set `DATABASE_URL` first, then run:

```powershell
python -m app.db.migrate
```

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
