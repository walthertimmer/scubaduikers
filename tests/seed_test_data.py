# seed_test_data.py
from datetime import date
from database import engine, get_session
from models import (
    User, DivingClub, DiveSite, Dive, UserDiveLink,
    UserDivingClubLink, ClubRole, JoinPolicy, DiveComment
)
from security import hash_password
from sqlmodel import Session, create_engine, SQLModel

def seed():
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # Clear existing data
        session.exec("DELETE FROM userdiveLink")
        session.exec("DELETE FROM userdivingclublink")
        session.exec("DELETE FROM divecomment")
        session.exec("DELETE FROM dive")
        session.exec("DELETE FROM divesite")
        session.exec("DELETE FROM user")
        session.exec("DELETE FROM divingclub")
        session.commit()

        # Create test users
        user1 = User(
            name="Alice",
            email="alice@test.com",
            password_hash=hash_password("alice123"),
            is_verified=True
        )
        user2 = User(
            name="Bob",
            email="bob@test.com",
            password_hash=hash_password("bob123"),
            is_verified=True
        )
        session.add_all([user1, user2])
        session.flush()

        # Create test clubs
        club = DivingClub(
            name="Test Dive Club",
            description="A test club",
            location="Amsterdam"
        )
        session.add(club)
        session.flush()

        # Create test dive sites
        # site1 = DiveSite(name="The Pit", location="Mexico", max_depth=120)
        # site2 = DiveSite(name="Blue Hole", location="Belize", max_depth=125)
        # session.add_all([site1, site2])
        # session.flush()

        # Add users to club
        session.add_all([
            UserDivingClubLink(user_id=user1.id, club_id=club.id, role=ClubRole.admin),
            UserDivingClubLink(user_id=user2.id, club_id=club.id, role=ClubRole.member),
        ])
        session.flush()

        # Create test dives
        dive1 = Dive(
            title="Weekend Dive",
            date=date(2026, 7, 15),
            site_id=site1.id,
            organiser_user_id=user1.id,
            organiser_club_id=club.id,
            join_policy=JoinPolicy.open
        )
        dive2 = Dive(
            title="Club Only Dive",
            date=date(2026, 7, 22),
            site_id=site2.id,
            organiser_user_id=user1.id,
            organiser_club_id=club.id,
            join_policy=JoinPolicy.club_only
        )
        dive3 = Dive(
            title="Secret Dive",
            date=date(2026, 8, 1),
            site_id=site1.id,
            organiser_user_id=user1.id,
            join_policy=JoinPolicy.password_protected,
            join_password_hash=hash_password("secret")
        )
        session.add_all([dive1, dive2, dive3])
        session.flush()

        # Add participants
        session.add_all([
            UserDiveLink(user_id=user1.id, dive_id=dive1.id),
            UserDiveLink(user_id=user2.id, dive_id=dive1.id),
            UserDiveLink(user_id=user1.id, dive_id=dive2.id),
        ])

        # Add comments
        session.add(DiveComment(
            dive_id=dive1.id,
            user_id=user2.id,
            content="Looking forward to this!"
        ))

        session.commit()
        print(f"Seed complete")

if __name__ == "__main__":
    seed()
