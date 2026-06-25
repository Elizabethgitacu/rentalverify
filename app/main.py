import os
from pathlib import Path

from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.storage import (
    authenticate,
    create_scam_report,
    dashboard_stats,
    demo_store,
    homepage_stats,
    log_search,
    register_landlord,
    search_landlord,
    search_timeline,
)


BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="RentalVerify")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("RVERIFY_SECRET_KEY", "dev-secret-change-me"),
    same_site="lax",
    https_only=False,
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def render(request: Request, template_name: str, **context):
    context.setdefault("request", request)
    context.setdefault("active_page", "")
    context.setdefault("current_user", request.session.get("user"))
    return templates.TemplateResponse(request=request, name=template_name, context=context)


def redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url=url, status_code=303)


def is_role(request: Request, role: str) -> bool:
    user = request.session.get("user")
    return bool(user and user.get("role") == role)


def demo_landlord_profile() -> dict:
    profile = demo_store.landlords[0].copy()
    profile["status"] = "Pending Review"
    return profile


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    featured_landlords = [
        {
            "name": landlord["name"],
            "location": landlord["location"].split(",")[0],
            "badge": landlord["status"],
            "reports": landlord["reports"],
        }
        for landlord in demo_store.landlords
    ]
    return render(
        request,
        "home.html",
        active_page="home",
        featured_landlords=featured_landlords,
        stats=homepage_stats(),
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


@app.post("/search", response_class=HTMLResponse)
def search_submit(
    request: Request,
    search_term: str = Form(...),
    search_type: str = Form("Any"),
    location: str = Form(""),
):
    landlord = search_landlord(search_term)
    log_search(
        search_term=search_term,
        search_type=search_type,
        location=location,
        result_status=landlord.get("status", "Unknown"),
        matched_landlord_id=landlord.get("id"),
    )
    return render(
        request,
        "search_result.html",
        active_page="search",
        landlord=landlord,
        search_term=search_term,
        search_type=search_type,
        location=location,
        report_timeline=search_timeline(),
    )


@app.get("/search/result", response_class=HTMLResponse)
def search_result(request: Request):
    landlord = demo_store.landlords[0].copy()
    return render(
        request,
        "search_result.html",
        active_page="search",
        landlord=landlord,
        report_timeline=search_timeline(),
    )


@app.get("/report", response_class=HTMLResponse)
def report_page(request: Request):
    return render(
        request,
        "report.html",
        active_page="report",
    )


@app.post("/report", response_class=HTMLResponse)
def report_submit(
    request: Request,
    reporter_name: str = Form(...),
    reporter_phone: str = Form(...),
    landlord_name: str = Form(...),
    landlord_phone: str = Form(...),
    national_id_number: str = Form(...),
    m_pesa_number: str = Form(...),
    property_address: str = Form(...),
    description: str = Form(...),
):
    reference = create_scam_report(
        {
            "reporter_name": reporter_name,
            "reporter_phone": reporter_phone,
            "landlord_name": landlord_name,
            "landlord_phone": landlord_phone,
            "national_id_number": national_id_number,
            "m_pesa_number": m_pesa_number,
            "property_address": property_address,
            "description": description,
        }
    )
    return redirect(f"/report/confirmation?reference={reference}")


@app.get("/report/confirmation", response_class=HTMLResponse)
def report_confirmation(request: Request, reference: str = Query(default="RV-2026-0042")):
    return render(
        request,
        "report_confirmation.html",
        active_page="report",
        reference=reference,
    )


@app.get("/landlord/register", response_class=HTMLResponse)
def landlord_register_page(request: Request):
    return render(
        request,
        "landlord_register.html",
        active_page="landlord_register",
    )


@app.post("/landlord/register", response_class=HTMLResponse)
def landlord_register_submit(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    phone_number: str = Form(...),
    national_id_number: str = Form(...),
    m_pesa_number: str = Form(...),
    property_location: str = Form(...),
    ownership_notes: str = Form(...),
):
    register_landlord(
        {
            "full_name": full_name,
            "email": email,
            "phone_number": phone_number,
            "national_id_number": national_id_number,
            "m_pesa_number": m_pesa_number,
            "property_location": property_location,
            "ownership_notes": ownership_notes,
        }
    )
    request.session["user"] = {"role": "landlord", "name": full_name, "email": email}
    request.session["landlord_profile"] = {
        "name": full_name,
        "phone": phone_number,
        "nid": national_id_number,
        "m_pesa": m_pesa_number,
        "location": property_location,
        "status": "Pending Review",
        "reports": 0,
    }
    return redirect("/landlord/dashboard")


@app.get("/landlord/login", response_class=HTMLResponse)
def landlord_login(request: Request):
    return render(
        request,
        "landlord_login.html",
        active_page="landlord_login",
    )


@app.post("/landlord/login", response_class=HTMLResponse)
def landlord_login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    if authenticate(email, password, "landlord"):
        request.session["user"] = {"role": "landlord", "email": email, "name": "Landlord"}
        request.session.setdefault("landlord_profile", demo_landlord_profile())
        return redirect("/landlord/dashboard")
    return render(
        request,
        "landlord_login.html",
        active_page="landlord_login",
        error="Invalid landlord credentials.",
    )


@app.get("/user/login", response_class=HTMLResponse)
def user_login(request: Request):
    return render(
        request,
        "user_login.html",
        active_page="user_login",
    )


@app.post("/user/login", response_class=HTMLResponse)
def user_login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    if authenticate(email, password, "user"):
        request.session["user"] = {"role": "user", "email": email, "name": "User"}
        return redirect("/search")
    return render(
        request,
        "user_login.html",
        active_page="user_login",
        error="Invalid user credentials.",
    )


@app.get("/landlord/dashboard", response_class=HTMLResponse)
def landlord_dashboard(request: Request):
    if not is_role(request, "landlord"):
        return redirect("/landlord/login")
    profile = request.session.get("landlord_profile") or demo_landlord_profile()
    return render(
        request,
        "landlord_dashboard.html",
        active_page="landlord_dashboard",
        profile=profile,
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


@app.post("/admin/login", response_class=HTMLResponse)
def admin_login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    if authenticate(email, password, "admin"):
        request.session["user"] = {"role": "admin", "email": email, "name": "Admin"}
        return redirect("/admin/dashboard")
    return render(
        request,
        "admin_login.html",
        active_page="admin_login",
        error="Invalid administrator credentials.",
    )


@app.get("/admin/access", response_class=HTMLResponse)
def admin_access(request: Request):
    return render(request, "admin_access.html", active_page="admin_access")


@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    if not is_role(request, "admin"):
        return redirect("/admin/login")
    stats = dashboard_stats()
    return render(
        request,
        "admin_dashboard.html",
        active_page="admin_dashboard",
        stats=stats,
        alerts=[
            f"{stats['pending']} landlord submissions need review",
            f"{stats['open_reports']} scam reports are open",
            f"{stats['escalated']} reports have been escalated",
        ],
    )


@app.get("/admin/landlords", response_class=HTMLResponse)
def admin_registration_review(request: Request):
    if not is_role(request, "admin"):
        return redirect("/admin/login")
    return render(
        request,
        "admin_registration_review.html",
        active_page="admin_landlords",
        pending_landlords=[item.copy() for item in demo_store.pending_landlords],
    )


@app.get("/admin/reports", response_class=HTMLResponse)
def admin_report_review(request: Request):
    if not is_role(request, "admin"):
        return redirect("/admin/login")
    return render(
        request,
        "admin_report_review.html",
        active_page="admin_reports",
        reports=[item.copy() for item in demo_store.reports],
    )


@app.get("/admin/analytics", response_class=HTMLResponse)
def admin_analytics(request: Request):
    if not is_role(request, "admin"):
        return redirect("/admin/login")
    stats = dashboard_stats()
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
        stats=stats,
    )


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return redirect("/")


@app.get("/404", response_class=HTMLResponse, status_code=404)
def not_found(request: Request):
    return render(request, "error_404.html", active_page="")
