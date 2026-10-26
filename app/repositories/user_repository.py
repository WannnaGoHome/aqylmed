from sqlalchemy.orm import Session

from app.core.timeutils import utcnow
from app.models.user import User, UserRole


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().lower()

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == self.normalize_email(email)).first()

    def list(self) -> list[User]:
        return self.db.query(User).order_by(User.created_at, User.id).all()

    def count(self) -> int:
        return self.db.query(User).count()

    def count_active_admins(self) -> int:
        return (
            self.db.query(User)
            .filter(User.role == UserRole.ADMIN, User.is_active.is_(True))
            .count()
        )

    def create(
        self, *, email: str, full_name: str, hashed_password: str, role: str, specialty_id: int | None = None
    ) -> User:
        user = User(
            email=self.normalize_email(email),
            full_name=full_name.strip(),
            hashed_password=hashed_password,
            role=role,
            specialty_id=specialty_id,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def touch_login(self, user: User) -> None:
        user.last_login_at = utcnow()
        self.db.commit()

    def save(self, user: User) -> User:
        self.db.commit()
        self.db.refresh(user)
        return user
