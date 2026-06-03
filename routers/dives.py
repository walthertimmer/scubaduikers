from datetime import date as date_type

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from sqlmodel import Session, select

from database import get_session
from models import (
    Dive,
    DiveComment,
    DiveSite,
    DivingClub,
    JoinPolicy,
    User,
    UserDiveLink,
    UserDivingClubLink,
)
from security import hash_password, verify_password
from templating import templates

router = APIRouter()


# ---------------------------------------------------------------------------
# Overview – upcoming dives
# ---------------------------------------------------------------------------

@router.get("/dives", response_class=HTMLResponse)
def dives_overview(request: Request, session: Session = Depends(get_session)):
    today = date_type.today()
    user_id = request.session.get("user_id")

    upcoming = session.exec(
        select(Dive).where(Dive.date >= today).order_by(Dive.date)
    ).all()

    # Pre-fetch user's club memberships and dive participations
    user_club_ids: set[int] = set()
    user_dive_ids: set[int] = set()
    if user_id:
        user_club_ids = {
            lnk.club_id
            for lnk in session.exec(
                select(UserDivingClubLink).where(UserDivingClubLink.user_id == user_id)
            ).all()
        }
        user_dive_ids = {
            lnk.dive_id
            for lnk in session.exec(
                select(UserDiveLink).where(UserDiveLink.user_id == user_id)
            ).all()
        }

    dive_data = []
    for dive in upcoming:
        site = session.get(DiveSite, dive.site_id)
        organiser_user = session.get(User, dive.organiser_user_id) if dive.organiser_user_id else None
        organiser_club = session.get(DivingClub, dive.organiser_club_id) if dive.organiser_club_id else None

        is_participant = dive.id in user_dive_ids
        can_join = False
        needs_password = False

        if user_id and not is_participant:
            if dive.join_policy == JoinPolicy.open:
                can_join = True
            elif dive.join_policy == JoinPolicy.club_only:
                can_join = bool(dive.organiser_club_id and dive.organiser_club_id in user_club_ids)
            elif dive.join_policy == JoinPolicy.password_protected:
                can_join = True
                needs_password = True

        participant_count = session.exec(
            select(UserDiveLink).where(UserDiveLink.dive_id == dive.id)
        ).all().__len__()

        dive_data.append({
            "dive": dive,
            "site": site,
            "organiser_user": organiser_user,
            "organiser_club": organiser_club,
            "is_participant": is_participant,
            "can_join": can_join,
            "needs_password": needs_password,
            "participant_count": participant_count,
        })

    flash_error = request.session.get("flash_error")
    if flash_error:
        del request.session["flash_error"]

    return templates.TemplateResponse(
        request, "dives.html", {"dive_data": dive_data, "flash_error": flash_error}
    )


# ---------------------------------------------------------------------------
# Create dive
# ---------------------------------------------------------------------------

@router.get("/dives/new", response_class=HTMLResponse)
def new_dive_page(request: Request, session: Session = Depends(get_session)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=303)

    links = session.exec(
        select(UserDivingClubLink).where(UserDivingClubLink.user_id == user_id)
    ).all()
    clubs = [session.get(DivingClub, lnk.club_id) for lnk in links]

    return templates.TemplateResponse(
        request, "dive_new.html",
        {"clubs": clubs, "error": None, "today": date_type.today().isoformat()},
    )


@router.post("/dives", response_class=HTMLResponse)
def create_dive(
    request: Request,
    title: str = Form(""),
    dive_date: str = Form(...),
    site_name: str = Form(...),
    site_location: str = Form(...),
    description: str = Form(""),
    club_id: str = Form(""),
    join_policy: str = Form("open"),
    join_password: str = Form(""),
    session: Session = Depends(get_session),
):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=303)

    # Validate date
    try:
        parsed_date = date_type.fromisoformat(dive_date)
    except ValueError:
        return _render_new_form(request, session, user_id, "Ongeldige datum.")

    parsed_club_id = int(club_id) if club_id else None
    parsed_policy = JoinPolicy(join_policy) if join_policy in JoinPolicy.__members__ else JoinPolicy.open

    # club_only requires a club selection
    if parsed_policy == JoinPolicy.club_only and not parsed_club_id:
        return _render_new_form(
            request, session, user_id,
            "Kies een club bij 'alleen voor clubleden'.",
        )

    # Password required for password_protected
    password_hash = None
    if parsed_policy == JoinPolicy.password_protected:
        if not join_password:
            return _render_new_form(
                request, session, user_id,
                "Voer een wachtwoord in voor een besloten duik.",
            )
        password_hash = hash_password(join_password)

    # Find or create dive site
    site = session.exec(
        select(DiveSite)
        .where(DiveSite.name == site_name)
        .where(DiveSite.location == site_location)
    ).first()
    if not site:
        site = DiveSite(name=site_name, location=site_location)
        session.add(site)
        session.flush()

    dive = Dive(
        title=title or None,
        date=parsed_date,
        site_id=site.id,
        description=description or None,
        organiser_user_id=user_id,
        organiser_club_id=parsed_club_id,
        join_policy=parsed_policy,
        join_password_hash=password_hash,
    )
    session.add(dive)
    session.flush()

    # Organiser is automatically a participant
    session.add(UserDiveLink(user_id=user_id, dive_id=dive.id))
    session.commit()
    return RedirectResponse("/dives", status_code=303)


def _render_new_form(request: Request, session: Session, user_id: int, error: str):
    links = session.exec(
        select(UserDivingClubLink).where(UserDivingClubLink.user_id == user_id)
    ).all()
    clubs = [session.get(DivingClub, lnk.club_id) for lnk in links]
    return templates.TemplateResponse(
        request, "dive_new.html",
        {"clubs": clubs, "error": error, "today": date_type.today().isoformat()},
        status_code=400,
    )


# ---------------------------------------------------------------------------
# Join dive
# ---------------------------------------------------------------------------

@router.post("/dives/{dive_id}/join")
def join_dive(
    dive_id: int,
    request: Request,
    password: str = Form(""),
    session: Session = Depends(get_session),
):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=303)

    dive = session.get(Dive, dive_id)
    if not dive:
        return RedirectResponse("/dives", status_code=303)

    # Already a participant?
    already = session.exec(
        select(UserDiveLink)
        .where(UserDiveLink.dive_id == dive_id)
        .where(UserDiveLink.user_id == user_id)
    ).first()
    if already:
        return RedirectResponse("/dives", status_code=303)

    # Policy checks
    if dive.join_policy == JoinPolicy.club_only:
        member = session.exec(
            select(UserDivingClubLink)
            .where(UserDivingClubLink.club_id == dive.organiser_club_id)
            .where(UserDivingClubLink.user_id == user_id)
        ).first()
        if not member:
            request.session["flash_error"] = "Je moet lid zijn van de organiserende club om mee te doen."
            return RedirectResponse(f"/dives/{dive_id}", status_code=303)

    if dive.join_policy == JoinPolicy.password_protected:
        if not dive.join_password_hash or not verify_password(dive.join_password_hash, password):
            request.session["flash_error"] = "Ongeldig wachtwoord."
            return RedirectResponse(f"/dives/{dive_id}", status_code=303)

    session.add(UserDiveLink(user_id=user_id, dive_id=dive_id))
    session.commit()
    return RedirectResponse(f"/dives/{dive_id}", status_code=303)


# ---------------------------------------------------------------------------
# Dive detail
# ---------------------------------------------------------------------------

@router.get("/dives/{dive_id}", response_class=HTMLResponse)
def dive_detail(dive_id: int, request: Request, session: Session = Depends(get_session)):
    dive = session.get(Dive, dive_id)
    if not dive:
        return RedirectResponse("/dives", status_code=303)

    user_id = request.session.get("user_id")

    site = session.get(DiveSite, dive.site_id)
    organiser_user = session.get(User, dive.organiser_user_id) if dive.organiser_user_id else None
    organiser_club = session.get(DivingClub, dive.organiser_club_id) if dive.organiser_club_id else None

    participants = session.exec(
        select(User)
        .join(UserDiveLink, UserDiveLink.user_id == User.id)
        .where(UserDiveLink.dive_id == dive_id)
    ).all()

    is_participant = any(p.id == user_id for p in participants)
    can_join = False
    needs_password = False

    if user_id and not is_participant:
        if dive.join_policy == JoinPolicy.open:
            can_join = True
        elif dive.join_policy == JoinPolicy.club_only:
            member = session.exec(
                select(UserDivingClubLink)
                .where(UserDivingClubLink.club_id == dive.organiser_club_id)
                .where(UserDivingClubLink.user_id == user_id)
            ).first()
            can_join = bool(member)
        elif dive.join_policy == JoinPolicy.password_protected:
            can_join = True
            needs_password = True

    flash_error = request.session.pop("flash_error", None)

    comments = session.exec(
        select(DiveComment).where(DiveComment.dive_id == dive_id).order_by(DiveComment.created_at)
    ).all()
    comment_users = {c.user_id: session.get(User, c.user_id) for c in comments}

    is_organiser = user_id is not None and dive.organiser_user_id == user_id

    return templates.TemplateResponse(
        request,
        "dive_detail.html",
        {
            "dive": dive,
            "site": site,
            "organiser_user": organiser_user,
            "organiser_club": organiser_club,
            "participants": participants,
            "is_participant": is_participant,
            "can_join": can_join,
            "needs_password": needs_password,
            "flash_error": flash_error,
            "comments": comments,
            "comment_users": comment_users,
            "is_organiser": is_organiser,
        },
    )


# ---------------------------------------------------------------------------
# Leave dive
# ---------------------------------------------------------------------------

@router.post("/dives/{dive_id}/leave")
def leave_dive(dive_id: int, request: Request, session: Session = Depends(get_session)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=303)

    link = session.exec(
        select(UserDiveLink)
        .where(UserDiveLink.dive_id == dive_id)
        .where(UserDiveLink.user_id == user_id)
    ).first()
    if link:
        session.delete(link)
        session.commit()

    return RedirectResponse(f"/dives/{dive_id}", status_code=303)


# ---------------------------------------------------------------------------
# Post a comment on a dive
# ---------------------------------------------------------------------------

@router.post("/dives/{dive_id}/comments")
def post_comment(
    dive_id: int,
    request: Request,
    content: str = Form(...),
    session: Session = Depends(get_session),
):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=303)

    dive = session.get(Dive, dive_id)
    if not dive:
        return RedirectResponse("/dives", status_code=303)

    content = content.strip()
    if content:
        session.add(DiveComment(dive_id=dive_id, user_id=user_id, content=content))
        session.commit()

    return RedirectResponse(f"/dives/{dive_id}#reacties", status_code=303)


# ---------------------------------------------------------------------------
# Edit dive (organiser only)
# ---------------------------------------------------------------------------

@router.get("/dives/{dive_id}/edit", response_class=HTMLResponse)
def edit_dive_page(dive_id: int, request: Request, session: Session = Depends(get_session)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=303)

    dive = session.get(Dive, dive_id)
    if not dive or dive.organiser_user_id != user_id:
        return RedirectResponse(f"/dives/{dive_id}", status_code=303)

    site = session.get(DiveSite, dive.site_id)
    links = session.exec(
        select(UserDivingClubLink).where(UserDivingClubLink.user_id == user_id)
    ).all()
    clubs = [session.get(DivingClub, lnk.club_id) for lnk in links]

    return templates.TemplateResponse(
        request, "dive_edit.html",
        {"dive": dive, "site": site, "clubs": clubs, "error": None},
    )


@router.post("/dives/{dive_id}/edit")
def edit_dive(
    dive_id: int,
    request: Request,
    title: str = Form(""),
    dive_date: str = Form(...),
    site_name: str = Form(...),
    site_location: str = Form(...),
    description: str = Form(""),
    club_id: str = Form(""),
    join_policy: str = Form("open"),
    join_password: str = Form(""),
    session: Session = Depends(get_session),
):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=303)

    dive = session.get(Dive, dive_id)
    if not dive or dive.organiser_user_id != user_id:
        return RedirectResponse(f"/dives/{dive_id}", status_code=303)

    try:
        parsed_date = date_type.fromisoformat(dive_date)
    except ValueError:
        return _render_edit_form(request, session, dive, user_id, "Ongeldige datum.")

    parsed_club_id = int(club_id) if club_id else None
    parsed_policy = JoinPolicy(join_policy) if join_policy in JoinPolicy.__members__ else JoinPolicy.open

    if parsed_policy == JoinPolicy.club_only and not parsed_club_id:
        return _render_edit_form(request, session, dive, user_id, "Kies een club bij 'alleen voor clubleden'.")

    if parsed_policy == JoinPolicy.password_protected and join_password:
        dive.join_password_hash = hash_password(join_password)
    elif parsed_policy != JoinPolicy.password_protected:
        dive.join_password_hash = None

    site = session.exec(
        select(DiveSite)
        .where(DiveSite.name == site_name)
        .where(DiveSite.location == site_location)
    ).first()
    if not site:
        site = DiveSite(name=site_name, location=site_location)
        session.add(site)
        session.flush()

    dive.title = title or None
    dive.date = parsed_date
    dive.site_id = site.id
    dive.description = description or None
    dive.organiser_club_id = parsed_club_id
    dive.join_policy = parsed_policy
    session.add(dive)
    session.commit()

    return RedirectResponse(f"/dives/{dive_id}", status_code=303)


def _render_edit_form(request, session, dive, user_id: int, error: str):
    site = session.get(DiveSite, dive.site_id)
    links = session.exec(
        select(UserDivingClubLink).where(UserDivingClubLink.user_id == user_id)
    ).all()
    clubs = [session.get(DivingClub, lnk.club_id) for lnk in links]
    return templates.TemplateResponse(
        request, "dive_edit.html",
        {"dive": dive, "site": site, "clubs": clubs, "error": error},
        status_code=400,
    )
