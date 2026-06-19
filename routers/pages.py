import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
import re

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from database import get_session
from mail import send_password_reset_email, send_verification_email
from models import User
from security import hash_password, verify_password
from templating import templates

router = APIRouter()
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html")


@router.get("/wijzigingen", response_class=HTMLResponse)
async def wijzigingen(request: Request):
    return templates.TemplateResponse(request, "wijzigingen.html")


@router.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    return templates.TemplateResponse(request, "contact.html")


@router.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    return templates.TemplateResponse(request, "privacy.html")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {"error": None})


@router.post("/register", response_class=HTMLResponse)
async def do_register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirmation: str = Form(...),
    phone: str = Form(...),
    session: Session = Depends(get_session),
):
    if phone:  # stop bots
        return templates.TemplateResponse(
            request,
            "register.html",
            {"error": None},
            status_code=400,
        )
    
    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        return templates.TemplateResponse(
            request, 
            "register.html", 
            {"error": "Ongeldig e-mailadres."}, 
            status_code=400
        )
    
    if len(password) < 8:
        return templates.TemplateResponse(
            request, 
            "register.html", 
            {"error": "Wachtwoord moet minstens 8 tekens lang zijn."}, 
            status_code=400
        )
    
    if password != password_confirmation:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"error": "De wachtwoorden komen niet overeen."},
            status_code=400,
        )
    
    if len(name) > 20:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"error": "Naam max 20 karakters."},
            status_code=400,
        )
    
    name = name.strip()[:20]
    if not name:
        return templates.TemplateResponse(
            request, 
            "register.html", 
            {"error": "Naam is vereist."}, 
            status_code=400
        )

    existing_name = session.exec(select(User).where(User.name == name)).first()
    if existing_name:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"error": "Deze naam is al in gebruik."},
            status_code=400,
        )

    existing_email = session.exec(select(User).where(User.email == email)).first()
    if existing_email:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"error": "Dit e-mailadres is al geregistreerd."},
            status_code=400,
        )

    token = secrets.token_urlsafe(32)
    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        verification_token=token,
        verification_sent_at=datetime.now(timezone.utc),
    )
    session.add(user)
    session.commit()

    base_url = str(request.base_url).rstrip("/")
    try:
        send_verification_email(email, token, base_url)
    except Exception:
        log.exception("Could not send verification email to %s", email)
        return templates.TemplateResponse(
            request,
            "register.html",
            {"error": "Account aangemaakt, maar de bevestigingsmail kon niet worden verstuurd. Neem contact op met de beheerder."},
            status_code=500,
        )

    return templates.TemplateResponse(request, "verify_pending.html", {"email": email})


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login", response_class=HTMLResponse)
async def do_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_session),
):
    user = db.exec(select(User).where(User.email == email)).first()
    if not user or not verify_password(user.password_hash, password):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Ongeldig e-mailadres of wachtwoord."},
            status_code=401,
        )
    if not user.is_verified:
        can_resend = (
            user.verification_sent_at is None
            or datetime.now(timezone.utc) - user.verification_sent_at.replace(tzinfo=timezone.utc) > timedelta(minutes=5)
        )
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "error": "Bevestig eerst je e-mailadres via de link in de bevestigingsmail.",
                "show_resend": can_resend,
                "resend_email": email,
            },
            status_code=403,
        )
    request.session["user_id"] = user.id
    request.session["user_name"] = user.name
    return RedirectResponse("/", status_code=303)


@router.post("/logout")
async def do_logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, session: Session = Depends(get_session)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=303)
    user = session.get(User, user_id)
    if not user:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request, "profile_edit.html", {"user": user, "saved": False})


@router.post("/profile", response_class=HTMLResponse)
async def update_profile(
    request: Request,
    description: str = Form(default=""),
    session: Session = Depends(get_session),
):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=303)
    user = session.get(User, user_id)
    if not user:
        return RedirectResponse("/login", status_code=303)
    user.description = description
    session.add(user)
    session.commit()
    session.refresh(user)
    return templates.TemplateResponse(request, "profile_edit.html", {"user": user, "saved": True})


# ---------------------------------------------------------------------------
# Public user profile
# ---------------------------------------------------------------------------

@router.get("/users/{user_id}", response_class=HTMLResponse)
async def public_profile_page(user_id: int, request: Request, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "user_profile.html", {"profile_user": user})


# ---------------------------------------------------------------------------
# Resend verification e-mail
# ---------------------------------------------------------------------------

@router.post("/resend-verification", response_class=HTMLResponse)
async def resend_verification(
    request: Request,
    email: str = Form(...),
    session: Session = Depends(get_session),
):
    user = session.exec(select(User).where(User.email == email)).first()
    if user and not user.is_verified:
        too_soon = (
            user.verification_sent_at is not None
            and datetime.now(timezone.utc) - user.verification_sent_at.replace(tzinfo=timezone.utc) < timedelta(minutes=5)
        )
        if not too_soon:
            token = secrets.token_urlsafe(32)
            user.verification_token = token
            user.verification_sent_at = datetime.now(timezone.utc)
            session.add(user)
            session.commit()
            base_url = str(request.base_url).rstrip("/")
            try:
                send_verification_email(email, token, base_url)
            except Exception:
                log.exception("Could not resend verification email to %s", email)
    return templates.TemplateResponse(request, "verify_pending.html", {"email": email})


# ---------------------------------------------------------------------------
# E-mail verification
# ---------------------------------------------------------------------------

@router.get("/verify/{token}", response_class=HTMLResponse)
async def verify_email(token: str, request: Request, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.verification_token == token)).first()
    if not user:
        return templates.TemplateResponse(
            request, "login.html",
            {"error": "Ongeldige of verlopen bevestigingslink."},
            status_code=400,
        )
    user.is_verified = True
    user.verification_token = None
    session.add(user)
    session.commit()
    return RedirectResponse("/login?verified=1", status_code=303)


# ---------------------------------------------------------------------------
# Forgot / reset password
# ---------------------------------------------------------------------------

@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse(request, "forgot_password.html", {"sent": False, "error": None})


@router.post("/forgot-password", response_class=HTMLResponse)
async def do_forgot_password(
    request: Request,
    email: str = Form(...),
    session: Session = Depends(get_session),
):
    user = session.exec(select(User).where(User.email == email)).first()
    # Always show the same response to avoid leaking whether the address exists
    if user and user.is_verified:
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        session.add(user)
        session.commit()
        base_url = str(request.base_url).rstrip("/")
        try:
            send_password_reset_email(email, token, base_url)
        except Exception:
            log.exception("Could not send password-reset email to %s", email)
    return templates.TemplateResponse(request, "forgot_password.html", {"sent": True, "error": None})


@router.get("/reset-password/{token}", response_class=HTMLResponse)
async def reset_password_page(token: str, request: Request, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.reset_token == token)).first()
    if not user or not user.reset_token_expires:
        return templates.TemplateResponse(
            request, "reset_password.html",
            {"token": token, "error": "Ongeldige of verlopen resetlink.", "done": False},
            status_code=400,
        )
    if datetime.now(timezone.utc) > user.reset_token_expires.replace(tzinfo=timezone.utc):
        return templates.TemplateResponse(
            request, "reset_password.html",
            {"token": token, "error": "Deze resetlink is verlopen. Vraag een nieuwe aan.", "done": False},
            status_code=400,
        )
    return templates.TemplateResponse(request, "reset_password.html", {"token": token, "error": None, "done": False})


@router.post("/reset-password/{token}", response_class=HTMLResponse)
async def do_reset_password(
    token: str,
    request: Request,
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    user = session.exec(select(User).where(User.reset_token == token)).first()
    if not user or not user.reset_token_expires:
        return templates.TemplateResponse(
            request, "reset_password.html",
            {"token": token, "error": "Ongeldige of verlopen resetlink.", "done": False},
            status_code=400,
        )
    if datetime.now(timezone.utc) > user.reset_token_expires.replace(tzinfo=timezone.utc):
        return templates.TemplateResponse(
            request, "reset_password.html",
            {"token": token, "error": "Deze resetlink is verlopen. Vraag een nieuwe aan.", "done": False},
            status_code=400,
        )
    user.password_hash = hash_password(password)
    user.reset_token = None
    user.reset_token_expires = None
    session.add(user)
    session.commit()
    return templates.TemplateResponse(request, "reset_password.html", {"token": token, "error": None, "done": True})

# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

@router.get("/superadmin", response_class=HTMLResponse)
async def admin_page(request: Request, session: Session = Depends(get_session)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=303)
    
    user = session.get(User, user_id)
    if not user or not user.is_superadmin:
        return RedirectResponse("/", status_code=403)
    
    # Calculate database size
    db_path = os.environ.get("DATABASE_PATH", "scubaduikers.db")
    db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
    db_size_mb = round(db_size / (1024 * 1024), 2)
    
    return templates.TemplateResponse(request, "superadmin.html", {"db_size_mb": db_size_mb})
