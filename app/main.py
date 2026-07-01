import os
from pathlib import Path

from fastapi import FastAPI, File, Form, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.mailer import send_admin_new_registration_email, send_email
from app.storage import (
    add_landlord_documents,
    approve_landlord,
    authenticate,
    close_report,
    create_account,
    create_booking_request,
    create_scam_report,
    dashboard_stats,
    demo_store,
    get_admin_emails,
    get_bnb_listing,
    get_booking_by_reference,
    get_landlord_documents,
    get_landlord_profile_by_email,
    get_pending_landlords,
    get_recent_reports,
    get_recent_searches,
    get_reports,
    get_tenant_profile_by_email,
    get_user_by_email_and_role,
    get_user_dashboard_overview,
    homepage_stats,
    escalate_report,
    list_bnb_listings,
    log_search,
    reject_landlord,
    search_landlord,
    search_timeline,
    update_landlord_profile,
    update_tenant_profile,
)


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
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
    current_user = request.session.get("user")
    context.setdefault("request", request)
    context.setdefault("active_page", "")
    context.setdefault("current_user", current_user)
    context.setdefault("dashboard_url", dashboard_url_for_role(current_user.get("role")) if current_user else "")
    return templates.TemplateResponse(request=request, name=template_name, context=context)


def redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url=url, status_code=303)


def is_role(request: Request, role: str) -> bool:
    user = request.session.get("user")
    if not user:
        return False
    current_role = user.get("role")
    if role == "tenant":
        return current_role in {"tenant", "user"}
    return current_role == role


def dashboard_url_for_role(role: str) -> str:
    return {
        "tenant": "/tenant/dashboard",
        "user": "/tenant/dashboard",
        "landlord": "/landlord/dashboard",
        "admin": "/admin/dashboard",
    }.get(role, "/")


def demo_landlord_profile() -> dict:
    profile = demo_store.landlords[0].copy()
    profile["status"] = "Pending Review"
    return profile


def _send_registration_email(full_name: str, email: str, role: str) -> None:
    subject = "Welcome to RentalVerify"
    body = (
        f"Hello {full_name},\n\n"
        f"Your {role} account has been created successfully on RentalVerify.\n"
        "You can now log in and continue with your profile setup or verification steps.\n\n"
        "If you did not create this account, please ignore this message.\n\n"
        "Kind regards,\n"
        "RentalVerify Team"
    )
    send_email(email, subject, body)


def _notify_admins_of_registration(full_name: str, email: str, role: str) -> None:
    for admin_email in get_admin_emails():
        send_admin_new_registration_email(admin_email, full_name, email, role)


def _send_login_email(email: str, role: str) -> None:
    user = get_user_by_email_and_role(email, role) or {}
    full_name = user.get("full_name") or role.title()
    subject = "RentalVerify sign-in notification"
    body = (
        f"Hello {full_name},\n\n"
        f"We noticed a successful sign-in to your RentalVerify {role} account.\n"
        "If this was you, no further action is needed.\n"
        "If you did not sign in, please review your account security immediately.\n\n"
        "Kind regards,\n"
        "RentalVerify Team"
    )
    send_email(email, subject, body)


def _save_upload(email: str, label: str, upload: UploadFile) -> str:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = upload.filename or f"{label}.bin"
    safe_name = safe_name.replace("/", "_").replace("\\", "_")
    target_dir = UPLOAD_DIR / email.replace("@", "_at_")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{label}_{safe_name}"
    with target_path.open("wb") as buffer:
        buffer.write(upload.file.read())
    return str(target_path)


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


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, role: str = Query(default="tenant")):
    role = role.lower()
    if role not in {"tenant", "landlord"}:
        role = "tenant"
    return render(
        request,
        "login.html",
        active_page="login",
        role=role,
    )


@app.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    role: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    role = role.lower()
    if role in {"user", "admin"}:
        role = "tenant"
    if authenticate(email, password, role):
        request.session["user"] = {"role": role, "email": email, "name": role.title()}
        if role == "landlord":
            request.session["landlord_profile"] = get_landlord_profile_by_email(email) or demo_landlord_profile()
        if role in {"tenant", "landlord"}:
            _send_login_email(email, role)
        return redirect(dashboard_url_for_role(role))
    return render(
        request,
        "login.html",
        active_page="login",
        role=role,
        error="Invalid credentials for that role.",
    )


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request, role: str = Query(default="tenant")):
    role = role.lower()
    if role not in {"tenant", "landlord"}:
        role = "tenant"
    return render(
        request,
        "register.html",
        active_page="register",
        role=role,
    )


@app.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    role: str = Form(...),
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone_number: str = Form(""),
    national_id_number: str = Form(""),
    m_pesa_number: str = Form(""),
    property_location: str = Form(""),
    ownership_notes: str = Form(""),
):
    role = role.lower()
    role = role.lower()
    if role not in {"tenant", "landlord"}:
        return render(request, "register.html", active_page="register", role="tenant", error="Choose Tenant or Landlord.")
    if role == "landlord" and not phone_number.strip():
        return render(request, "register.html", active_page="register", role=role, error="Landlord registration needs a phone number.")
    try:
        account = create_account(
            {
                "role": role,
                "full_name": full_name,
                "email": email,
                "password": password,
                "phone_number": phone_number,
                "national_id_number": national_id_number,
                "m_pesa_number": m_pesa_number,
                "property_location": property_location,
                "ownership_notes": ownership_notes,
            }
        )
    except Exception as exc:
        return render(request, "register.html", active_page="register", role=role, error=str(exc))

    if role == "tenant":
        request.session["user"] = {"role": role, "email": email, "name": full_name}
        _send_registration_email(full_name, email, role)
        _notify_admins_of_registration(full_name, email, role)
        return redirect(dashboard_url_for_role(role))

    _send_registration_email(full_name, email, role)
    _notify_admins_of_registration(full_name, email, role)
    return render(
        request,
        "login.html",
        active_page="login",
        role="landlord",
        error="Registration received. Your landlord account is pending verification and cannot sign in yet.",
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


@app.get("/bnb", response_class=HTMLResponse)
def bnb_page(
    request: Request,
    area: str = Query(default=""),
    guests: int = Query(default=0),
    max_price: int = Query(default=0),
):
    listings = list_bnb_listings(area=area, guests=guests, max_price=max_price)
    return render(
        request,
        "bnb.html",
        active_page="bnb",
        listings=listings,
        filters={"area": area, "guests": guests or "", "max_price": max_price or ""},
        featured_listing=listings[0] if listings else None,
    )


@app.post("/bnb/book", response_class=HTMLResponse)
def bnb_book_submit(
    request: Request,
    listing_id: int = Form(...),
    guest_name: str = Form(...),
    guest_email: str = Form(...),
    guest_phone: str = Form(...),
    guests: int = Form(...),
    check_in: str = Form(...),
    check_out: str = Form(...),
    special_requests: str = Form(""),
):
    listing = get_bnb_listing(listing_id)
    error = None
    if not listing:
        error = "Select a valid listing to book."
    elif check_in >= check_out:
        error = "Check-out date must be after check-in date."
    elif guests > listing["max_guests"]:
        error = f"{listing['name']} sleeps up to {listing['max_guests']} guests."

    if error:
        listings = list_bnb_listings()
        return render(
            request,
            "bnb.html",
            active_page="bnb",
            listings=listings,
            filters={"area": "", "guests": guests, "max_price": ""},
            featured_listing=listing,
            error=error,
        )

    reference = create_booking_request(
        {
            "listing_id": listing_id,
            "guest_name": guest_name,
            "guest_email": guest_email,
            "guest_phone": guest_phone,
            "check_in": check_in,
            "check_out": check_out,
            "guests": guests,
            "special_requests": special_requests,
        }
    )
    return redirect(f"/bnb/confirmation?reference={reference}")


@app.get("/bnb/confirmation", response_class=HTMLResponse)
def bnb_confirmation(request: Request, reference: str = Query(default="")):
    booking = get_booking_by_reference(reference) if reference else None
    return render(
        request,
        "bnb_confirmation.html",
        active_page="bnb",
        booking=booking,
        reference=reference,
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
    return redirect("/register?role=landlord")


@app.post("/landlord/register", response_class=HTMLResponse)
def landlord_register_submit(request: Request):
    return redirect("/register?role=landlord")


@app.get("/landlord/login", response_class=HTMLResponse)
def landlord_login(request: Request):
    return redirect("/login?role=landlord")


@app.post("/landlord/login", response_class=HTMLResponse)
def landlord_login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    if authenticate(email, password, "landlord"):
        request.session["user"] = {"role": "landlord", "email": email, "name": "Landlord"}
        request.session["landlord_profile"] = get_landlord_profile_by_email(email) or demo_landlord_profile()
        _send_login_email(email, "landlord")
        return redirect("/landlord/dashboard")
    account = get_user_by_email_and_role(email, "landlord")
    if account and int(account.get("is_active", 0)) != 1:
        return render(request, "login.html", active_page="login", role="landlord", error="Your landlord account is pending verification. Please wait for approval before signing in.")
    return render(request, "login.html", active_page="login", role="landlord", error="Invalid credentials for that role.")


@app.get("/tenant/login", response_class=HTMLResponse)
def tenant_login(request: Request):
    return redirect("/login?role=tenant")


@app.get("/user/login", response_class=HTMLResponse)
def user_login(request: Request):
    return redirect("/login?role=tenant")


@app.post("/tenant/login", response_class=HTMLResponse)
def tenant_login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    if authenticate(email, password, "tenant"):
        request.session["user"] = {"role": "tenant", "email": email, "name": "Tenant"}
        _send_login_email(email, "tenant")
        return redirect("/tenant/dashboard")
    account = get_user_by_email_and_role(email, "tenant")
    if account and int(account.get("is_active", 0)) != 1:
        return render(request, "login.html", active_page="login", role="tenant", error="Your account is pending verification. Please wait for approval before signing in.")
    return render(request, "login.html", active_page="login", role="tenant", error="Invalid credentials for that role.")


@app.post("/user/login", response_class=HTMLResponse)
def user_login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    return tenant_login_submit(request, email=email, password=password)


@app.get("/tenant/dashboard", response_class=HTMLResponse)
def tenant_dashboard(request: Request):
    if not is_role(request, "tenant"):
        return redirect("/login?role=tenant")
    user = request.session.get("user") or {}
    profile = get_tenant_profile_by_email(user.get("email", "")) or {"national_id_number": "", "m_pesa_number": "", "profile_status": "incomplete"}
    return render(
        request,
        "tenant_dashboard.html",
        active_page="tenant_dashboard",
        profile=profile,
        overview=get_user_dashboard_overview(),
        recent_searches=get_recent_searches(),
        recent_reports=get_recent_reports(),
    )


@app.get("/user/dashboard", response_class=HTMLResponse)
def user_dashboard(request: Request):
    return redirect("/tenant/dashboard")


@app.post("/tenant/profile")
def tenant_profile_submit(
    request: Request,
    national_id_number: str = Form(...),
    m_pesa_number: str = Form(...),
):
    if not is_role(request, "tenant"):
        return redirect("/login?role=tenant")
    user = request.session.get("user") or {}
    update_tenant_profile(user.get("email", ""), national_id_number, m_pesa_number)
    return redirect("/tenant/dashboard")


@app.get("/landlord/dashboard", response_class=HTMLResponse)
def landlord_dashboard(request: Request):
    if not is_role(request, "landlord"):
        return redirect("/login?role=landlord")
    user = request.session.get("user") or {}
    profile = request.session.get("landlord_profile") or get_landlord_profile_by_email(user.get("email", "")) or demo_landlord_profile()
    documents = get_landlord_documents(user.get("email", ""))
    return render(
        request,
        "landlord_dashboard.html",
        active_page="landlord_dashboard",
        profile=profile,
        documents=documents,
    )


@app.post("/landlord/profile")
def landlord_profile_submit(
    request: Request,
    national_id_number: str = Form(...),
    m_pesa_number: str = Form(...),
    property_location: str = Form(...),
    ownership_notes: str = Form(""),
):
    if not is_role(request, "landlord"):
        return redirect("/login?role=landlord")
    user = request.session.get("user") or {}
    update_landlord_profile(user.get("email", ""), national_id_number, m_pesa_number, property_location, ownership_notes)
    request.session["landlord_profile"] = get_landlord_profile_by_email(user.get("email", "")) or demo_landlord_profile()
    return redirect("/landlord/dashboard")


@app.post("/landlord/documents")
async def landlord_documents_submit(
    request: Request,
    id_copy: UploadFile | None = File(default=None),
    ownership_document: UploadFile | None = File(default=None),
    passport_photo: UploadFile | None = File(default=None),
):
    if not is_role(request, "landlord"):
        return redirect("/login?role=landlord")
    user = request.session.get("user") or {}
    docs = []
    for label, upload in [
        ("ID copy", id_copy),
        ("Ownership document", ownership_document),
        ("Passport photo", passport_photo),
    ]:
        if upload and upload.filename:
            docs.append((label, _save_upload(user.get("email", ""), label.replace(" ", "_"), upload)))
    if docs:
        add_landlord_documents(user.get("email", ""), docs)
    return redirect("/landlord/dashboard")


@app.get("/admin/login", response_class=HTMLResponse)
def admin_login(request: Request):
    return render(request, "admin_login.html", active_page="admin_login")


@app.post("/admin/login", response_class=HTMLResponse)
def admin_login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    if authenticate(email, password, "admin"):
        request.session["user"] = {"role": "admin", "email": email, "name": "Admin"}
        return redirect("/admin/dashboard")
    return render(request, "admin_login.html", active_page="admin_login", error="Invalid admin credentials.")


@app.get("/admin/access", response_class=HTMLResponse)
def admin_access(request: Request):
    return render(request, "admin_access.html", active_page="admin_access")


@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, email_status: str = Query(default=""), email_message: str = Query(default="")):
    if not is_role(request, "admin"):
        return redirect("/login?role=admin")
    stats = dashboard_stats()
    user = request.session.get("user") or {}
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
        email_status=email_status,
        email_message=email_message,
        email_recipient=user.get("email", ""),
    )


@app.get("/admin/landlords", response_class=HTMLResponse)
def admin_registration_review(request: Request):
    if not is_role(request, "admin"):
        return redirect("/login?role=admin")
    return render(
        request,
        "admin_registration_review.html",
        active_page="admin_landlords",
        pending_landlords=get_pending_landlords(),
    )


@app.get("/admin/reports", response_class=HTMLResponse)
def admin_report_review(request: Request):
    if not is_role(request, "admin"):
        return redirect("/login?role=admin")
    return render(
        request,
        "admin_report_review.html",
        active_page="admin_reports",
        reports=get_reports(),
    )


@app.get("/admin/analytics", response_class=HTMLResponse)
def admin_analytics(request: Request):
    if not is_role(request, "admin"):
        return redirect("/login?role=admin")
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


@app.get("/dashboard")
def dashboard_home(request: Request):
    user = request.session.get("user")
    if not user:
        return redirect("/login")
    return redirect(dashboard_url_for_role(user.get("role", "")))


@app.post("/admin/landlords/{landlord_id}/approve")
def admin_landlord_approve(request: Request, landlord_id: int):
    if not is_role(request, "admin"):
        return redirect("/login?role=admin")
    approve_landlord(landlord_id, actor_user_id=None)
    return redirect("/admin/landlords")


@app.post("/admin/landlords/{landlord_id}/reject")
def admin_landlord_reject(request: Request, landlord_id: int, reason: str = Form("")):
    if not is_role(request, "admin"):
        return redirect("/login?role=admin")
    reject_landlord(landlord_id, reason=reason, actor_user_id=None)
    return redirect("/admin/landlords")


@app.post("/admin/reports/{report_id}/escalate")
def admin_report_escalate(request: Request, report_id: int):
    if not is_role(request, "admin"):
        return redirect("/login?role=admin")
    escalate_report(report_id, actor_user_id=None)
    return redirect("/admin/reports")


@app.post("/admin/reports/{report_id}/close")
def admin_report_close(request: Request, report_id: int):
    if not is_role(request, "admin"):
        return redirect("/login?role=admin")
    close_report(report_id, actor_user_id=None)
    return redirect("/admin/reports")


@app.post("/admin/test-email")
def admin_test_email(
    request: Request,
    recipient_email: str = Form(...),
    subject: str = Form(default="RentalVerify test email"),
    message: str = Form(default="This is a test from RentalVerify."),
):
    if not is_role(request, "admin"):
        return redirect("/login?role=admin")
    ok = send_email(recipient_email, subject, message)
    status = "success" if ok else "error"
    msg = "Test email sent." if ok else "Test email failed. Check SMTP settings and app password."
    return redirect(f"/admin/dashboard?email_status={status}&email_message={msg}")


@app.get("/404", response_class=HTMLResponse, status_code=404)
def not_found(request: Request):
    return render(request, "error_404.html", active_page="")
