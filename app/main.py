from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="RentalVerify Prototype")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def render(request: Request, template_name: str, **context):
    context.setdefault("request", request)
    context.setdefault("active_page", "")
    return templates.TemplateResponse(request=request, name=template_name, context=context)


sample_landlord = {
    "name": "Muriuki Property Services",
    "phone": "+254 712 456 789",
    "nid": "2714 8891 2456",
    "m_pesa": "254712456789",
    "location": "Kilimani, Nairobi",
    "status": "Verified",
    "reports": 3,
}

sample_reports = [
    {
        "ref": "RV-2026-0042",
        "landlord": "Muriuki Property Services",
        "status": "Open",
        "risk": "High",
        "date": "2026-06-18",
    },
    {
        "ref": "RV-2026-0039",
        "landlord": "Amani Rentals",
        "status": "Under Review",
        "risk": "Medium",
        "date": "2026-06-15",
    },
    {
        "ref": "RV-2026-0031",
        "landlord": "Nairobi Homes Agency",
        "status": "Escalated",
        "risk": "High",
        "date": "2026-06-10",
    },
]

sample_pending_landlords = [
    {
        "name": "Muriuki Property Services",
        "phone": "+254 712 456 789",
        "location": "Kilimani",
        "submitted": "2026-06-20",
    },
    {
        "name": "Rongai Lettings",
        "phone": "+254 733 000 445",
        "location": "Langata",
        "submitted": "2026-06-21",
    },
]


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    featured_landlords = [
        {
            "name": "Muriuki Property Services",
            "location": "Kilimani",
            "badge": "Verified",
            "reports": 3,
        },
        {
            "name": "Lakeside Residences",
            "location": "Kileleshwa",
            "badge": "Verified",
            "reports": 1,
        },
        {
            "name": "Sunrise Court",
            "location": "South B",
            "badge": "Reported",
            "reports": 7,
        },
    ]
    return render(
        request,
        "home.html",
        active_page="home",
        featured_landlords=featured_landlords,
        stats={
            "searches": "14,820",
            "reports": "1,246",
            "verified": "382",
            "resolved": "91%",
        },
    )


@app.get("/search", response_class=HTMLResponse)
def search_page(request: Request):
    return render(
        request,
        "search.html",
        active_page="search",
        recent_searches=[
            "0712 456 789",
            "Muriuki Property Services",
            "254712456789",
            "Kilimani landlord",
        ],
    )


@app.get("/search/result", response_class=HTMLResponse)
def search_result(request: Request):
    return render(
        request,
        "search_result.html",
        active_page="search",
        landlord=sample_landlord,
        report_timeline=[
            {"date": "2026-06-12", "note": "First report submitted"},
            {"date": "2026-06-15", "note": "Admin review started"},
            {"date": "2026-06-18", "note": "Status marked high risk"},
        ],
    )


@app.get("/report", response_class=HTMLResponse)
def report_page(request: Request):
    return render(
        request,
        "report.html",
        active_page="report",
    )


@app.get("/report/confirmation", response_class=HTMLResponse)
def report_confirmation(request: Request):
    return render(
        request,
        "report_confirmation.html",
        active_page="report",
        reference="RV-2026-0042",
    )


@app.get("/landlord/register", response_class=HTMLResponse)
def landlord_register(request: Request):
    return render(
        request,
        "landlord_register.html",
        active_page="landlord_register",
    )


@app.get("/landlord/login", response_class=HTMLResponse)
def landlord_login(request: Request):
    return render(
        request,
        "landlord_login.html",
        active_page="landlord_login",
    )


@app.get("/landlord/dashboard", response_class=HTMLResponse)
def landlord_dashboard(request: Request):
    return render(
        request,
        "landlord_dashboard.html",
        active_page="landlord_dashboard",
        profile=sample_landlord,
        documents=[
            "National ID copy",
            "Property ownership document",
            "Passport photo",
            "Phone number confirmation",
        ],
    )


@app.get("/admin/login", response_class=HTMLResponse)
def admin_login(request: Request):
    return render(
        request,
        "admin_login.html",
        active_page="admin_login",
    )


@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    return render(
        request,
        "admin_dashboard.html",
        active_page="admin_dashboard",
        stats={
            "pending": 12,
            "open_reports": 8,
            "escalated": 4,
            "verified_this_week": 9,
        },
        alerts=[
            "3 new high-risk reports need review",
            "2 landlord submissions are missing ID documents",
            "1 report has crossed escalation threshold",
        ],
    )


@app.get("/admin/landlords", response_class=HTMLResponse)
def admin_registration_review(request: Request):
    return render(
        request,
        "admin_registration_review.html",
        active_page="admin_landlords",
        pending_landlords=sample_pending_landlords,
    )


@app.get("/admin/reports", response_class=HTMLResponse)
def admin_report_review(request: Request):
    return render(
        request,
        "admin_report_review.html",
        active_page="admin_reports",
        reports=sample_reports,
    )


@app.get("/admin/analytics", response_class=HTMLResponse)
def admin_analytics(request: Request):
    return render(
        request,
        "admin_analytics.html",
        active_page="admin_analytics",
        kpis=[
            {"label": "Searches", "value": "14,820"},
            {"label": "Reports", "value": "1,246"},
            {"label": "Verified", "value": "382"},
            {"label": "Escalation rate", "value": "18%"},
        ],
        bars=[
            {"label": "Searches", "value": 92},
            {"label": "Reports", "value": 68},
            {"label": "Approvals", "value": 74},
            {"label": "Escalations", "value": 41},
            {"label": "Resolved", "value": 88},
        ],
    )


@app.get("/404", response_class=HTMLResponse, status_code=404)
def not_found(request: Request):
    return render(request, "error_404.html", active_page=""),
