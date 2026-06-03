from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from sqlmodel import Session, select

from database import get_session
from models import (
    ClubJoinRequest,
    ClubRole,
    DivingClub,
    JoinRequestStatus,
    User,
    UserDivingClubLink,
)
from templating import templates

router = APIRouter()


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

@router.get("/clubs", response_class=HTMLResponse)
def clubs_overview(request: Request, session: Session = Depends(get_session)):
    clubs = session.exec(select(DivingClub)).all()
    user_id = request.session.get("user_id")

    club_data = []
    for club in clubs:
        entry: dict = {
            "club": club,
            "user_role": None,
            "has_pending_request": False,
            "pending_requests": [],
        }

        if user_id:
            link = session.exec(
                select(UserDivingClubLink)
                .where(UserDivingClubLink.club_id == club.id)
                .where(UserDivingClubLink.user_id == user_id)
            ).first()

            if link:
                entry["user_role"] = link.role
            else:
                req = session.exec(
                    select(ClubJoinRequest)
                    .where(ClubJoinRequest.club_id == club.id)
                    .where(ClubJoinRequest.user_id == user_id)
                    .where(ClubJoinRequest.status == JoinRequestStatus.pending)
                ).first()
                entry["has_pending_request"] = req is not None

            if link and link.role == ClubRole.admin:
                pending = session.exec(
                    select(ClubJoinRequest)
                    .where(ClubJoinRequest.club_id == club.id)
                    .where(ClubJoinRequest.status == JoinRequestStatus.pending)
                ).all()
                entry["pending_requests"] = [
                    {"request": r, "user": session.get(User, r.user_id)}
                    for r in pending
                ]

        club_data.append(entry)

    return templates.TemplateResponse(request, "clubs.html", {"club_data": club_data})


# ---------------------------------------------------------------------------
# Create club
# ---------------------------------------------------------------------------

@router.get("/clubs/new", response_class=HTMLResponse)
def new_club_page(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request, "club_new.html", {"error": None})


# ---------------------------------------------------------------------------
# Club detail
# ---------------------------------------------------------------------------

@router.get("/clubs/{club_id}", response_class=HTMLResponse)
def club_detail(club_id: int, request: Request, session: Session = Depends(get_session)):
    club = session.get(DivingClub, club_id)
    if not club:
        return RedirectResponse("/clubs", status_code=303)

    user_id = request.session.get("user_id")

    # Members with their roles
    links = session.exec(
        select(UserDivingClubLink).where(UserDivingClubLink.club_id == club_id)
    ).all()
    members = [
        {"user": session.get(User, lnk.user_id), "role": lnk.role}
        for lnk in links
    ]

    # Current user's relationship to this club
    user_role = None
    has_pending_request = False
    pending_requests = []

    if user_id:
        my_link = session.exec(
            select(UserDivingClubLink)
            .where(UserDivingClubLink.club_id == club_id)
            .where(UserDivingClubLink.user_id == user_id)
        ).first()

        if my_link:
            user_role = my_link.role
        else:
            req = session.exec(
                select(ClubJoinRequest)
                .where(ClubJoinRequest.club_id == club_id)
                .where(ClubJoinRequest.user_id == user_id)
                .where(ClubJoinRequest.status == JoinRequestStatus.pending)
            ).first()
            has_pending_request = req is not None

        if my_link and my_link.role == ClubRole.admin:
            pending = session.exec(
                select(ClubJoinRequest)
                .where(ClubJoinRequest.club_id == club_id)
                .where(ClubJoinRequest.status == JoinRequestStatus.pending)
            ).all()
            pending_requests = [
                {"request": r, "user": session.get(User, r.user_id)}
                for r in pending
            ]

    return templates.TemplateResponse(request, "club_detail.html", {
        "club": club,
        "members": members,
        "user_role": user_role,
        "has_pending_request": has_pending_request,
        "pending_requests": pending_requests,
    })


@router.post("/clubs", response_class=HTMLResponse)
def create_club(
    request: Request,
    name: str = Form(...),
    location: str = Form(""),
    website: str = Form(""),
    session: Session = Depends(get_session),
):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=303)

    club = DivingClub(
        name=name,
        location=location or None,
        website=website or None,
    )
    session.add(club)
    session.flush()  # populate club.id before creating the link

    link = UserDivingClubLink(user_id=user_id, club_id=club.id, role=ClubRole.admin)
    session.add(link)
    session.commit()
    return RedirectResponse("/clubs", status_code=303)


# ---------------------------------------------------------------------------
# Join request
# ---------------------------------------------------------------------------

@router.post("/clubs/{club_id}/join", response_class=HTMLResponse)
def request_join(
    club_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=303)

    # Ignore if already a member or already has a pending request
    already_member = session.exec(
        select(UserDivingClubLink)
        .where(UserDivingClubLink.club_id == club_id)
        .where(UserDivingClubLink.user_id == user_id)
    ).first()
    if not already_member:
        existing_req = session.exec(
            select(ClubJoinRequest)
            .where(ClubJoinRequest.club_id == club_id)
            .where(ClubJoinRequest.user_id == user_id)
            .where(ClubJoinRequest.status == JoinRequestStatus.pending)
        ).first()
        if not existing_req:
            session.add(ClubJoinRequest(user_id=user_id, club_id=club_id))
            session.commit()

    return RedirectResponse(f"/clubs/{club_id}", status_code=303)
# ---------------------------------------------------------------------------

def _get_admin_link(club_id: int, user_id: int, session: Session):
    link = session.exec(
        select(UserDivingClubLink)
        .where(UserDivingClubLink.club_id == club_id)
        .where(UserDivingClubLink.user_id == user_id)
    ).first()
    return link if (link and link.role == ClubRole.admin) else None


@router.post("/clubs/{club_id}/requests/{request_id}/approve")
def approve_request(
    club_id: int,
    request_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    user_id = request.session.get("user_id")
    if not user_id or not _get_admin_link(club_id, user_id, session):
        return RedirectResponse("/clubs", status_code=303)

    join_req = session.get(ClubJoinRequest, request_id)
    if not join_req or join_req.club_id != club_id:
        return RedirectResponse("/clubs", status_code=303)

    join_req.status = JoinRequestStatus.approved
    session.add(UserDivingClubLink(user_id=join_req.user_id, club_id=club_id, role=ClubRole.member))
    session.commit()
    return RedirectResponse(f"/clubs/{club_id}", status_code=303)


@router.post("/clubs/{club_id}/requests/{request_id}/reject")
def reject_request(
    club_id: int,
    request_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    user_id = request.session.get("user_id")
    if not user_id or not _get_admin_link(club_id, user_id, session):
        return RedirectResponse("/clubs", status_code=303)

    join_req = session.get(ClubJoinRequest, request_id)
    if not join_req or join_req.club_id != club_id:
        return RedirectResponse("/clubs", status_code=303)

    join_req.status = JoinRequestStatus.rejected
    session.commit()
    return RedirectResponse(f"/clubs/{club_id}", status_code=303)


# ---------------------------------------------------------------------------
# Edit club (admin only)
# ---------------------------------------------------------------------------

@router.get("/clubs/{club_id}/edit", response_class=HTMLResponse)
def edit_club_page(club_id: int, request: Request, session: Session = Depends(get_session)):
    user_id = request.session.get("user_id")
    if not user_id or not _get_admin_link(club_id, user_id, session):
        return RedirectResponse(f"/clubs/{club_id}", status_code=303)

    club = session.get(DivingClub, club_id)
    if not club:
        return RedirectResponse("/clubs", status_code=303)

    return templates.TemplateResponse(request, "club_edit.html", {"club": club, "error": None})


@router.post("/clubs/{club_id}/edit", response_class=HTMLResponse)
def edit_club(
    club_id: int,
    request: Request,
    name: str = Form(...),
    location: str = Form(""),
    website: str = Form(""),
    session: Session = Depends(get_session),
):
    user_id = request.session.get("user_id")
    if not user_id or not _get_admin_link(club_id, user_id, session):
        return RedirectResponse(f"/clubs/{club_id}", status_code=303)

    club = session.get(DivingClub, club_id)
    if not club:
        return RedirectResponse("/clubs", status_code=303)

    club.name = name
    club.location = location or None
    club.website = website or None
    session.add(club)
    session.commit()
    return RedirectResponse(f"/clubs/{club_id}", status_code=303)
