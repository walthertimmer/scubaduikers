"""Database models"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint


# ---------------------------------------------------------------------------
# Many-to-many link: User <-> DivingClub
# ---------------------------------------------------------------------------

class ClubRole(str, Enum):
    member = "member"
    admin  = "admin"


class UserDivingClubLink(SQLModel, table=True):
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", primary_key=True)
    club_id: Optional[int] = Field(default=None, foreign_key="divingclub.id", primary_key=True)
    role: ClubRole = Field(default=ClubRole.member)


# ---------------------------------------------------------------------------
# Many-to-many link: User <-> Dive (participants)
# ---------------------------------------------------------------------------

class UserDiveLink(SQLModel, table=True):
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", primary_key=True)
    dive_id: Optional[int] = Field(default=None, foreign_key="dive.id", primary_key=True)


# ---------------------------------------------------------------------------
# DivingClub
# ---------------------------------------------------------------------------

class DivingClubBase(SQLModel):
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None


class DivingClub(DivingClubBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    members: list["User"] = Relationship(back_populates="clubs", link_model=UserDivingClubLink)
    organised_dives: list["Dive"] = Relationship(back_populates="organiser_club")


class DivingClubCreate(DivingClubBase):
    pass


class DivingClubRead(DivingClubBase):
    id: int


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class UserBase(SQLModel):
    name: str
    email: str
    description: Optional[str] = None


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    password_hash: Optional[str] = Field(default=None)
    is_verified: bool = Field(default=False)
    is_superadmin: bool = Field(default=False)
    verification_token: Optional[str] = Field(default=None)
    verification_sent_at: Optional[datetime] = Field(default=None)
    reset_token: Optional[str] = Field(default=None)
    reset_token_expires: Optional[datetime] = Field(default=None)

    clubs: list[DivingClub] = Relationship(back_populates="members", link_model=UserDivingClubLink)
    dives: list["Dive"] = Relationship(back_populates="divers", link_model=UserDiveLink)
    organised_dives: list["Dive"] = Relationship(back_populates="organiser_user")


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: int


# ---------------------------------------------------------------------------
# Dive
# organize group dive with multiple divers 
# ---------------------------------------------------------------------------

class JoinPolicy(str, Enum):
    open               = "open"
    club_only          = "club_only"
    password_protected = "password_protected"


class DiveBase(SQLModel):
    date: date
    title: Optional[str] = None
    location: str
    description: Optional[str] = None
    organiser_club_id: Optional[int] = Field(default=None, foreign_key="divingclub.id")
    organiser_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    join_policy: JoinPolicy = Field(default=JoinPolicy.open)
    join_password_hash: Optional[str] = Field(default=None)


class Dive(DiveBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    divers: list[User] = Relationship(back_populates="dives", link_model=UserDiveLink)
    organiser_club: Optional[DivingClub] = Relationship(back_populates="organised_dives")
    organiser_user: Optional[User] = Relationship(back_populates="organised_dives")


class DiveCreate(DiveBase):
    pass


class DiveRead(DiveBase):
    id: int


# ---------------------------------------------------------------------------
# Dive comments
# ---------------------------------------------------------------------------

class DiveComment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    dive_id: int = Field(foreign_key="dive.id")
    user_id: int = Field(foreign_key="user.id")
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Club join requests
# ---------------------------------------------------------------------------

class JoinRequestStatus(str, Enum):
    pending  = "pending"
    approved = "approved"
    rejected = "rejected"


class ClubJoinRequest(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("user_id", "club_id", name="uq_join_request"),)

    id:      Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    club_id: int = Field(foreign_key="divingclub.id")
    status:  JoinRequestStatus = Field(default=JoinRequestStatus.pending)
