import hashlib
import re
import secrets
from uuid import UUID

from internal.domain.errors import ErrInvalidInput
from internal.domain.models import User
from internal.repository.contracts import UserRepository


class UserService:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    @staticmethod
    def _validate(email: str, display_name: str) -> tuple[str, str]:
        email, display_name = email.strip().lower(), display_name.strip()
        if len(email) > 255 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise ErrInvalidInput("Email must have a valid format and at most 255 characters.")
        if not 2 <= len(display_name) <= 100:
            raise ErrInvalidInput("Display name must contain 2 to 100 characters.")
        return email, display_name

    def create(self, email: str, password: str, display_name: str) -> User:
        email, display_name = self._validate(email, display_name)
        if not 8 <= len(password) <= 128:
            raise ErrInvalidInput("Password must contain 8 to 128 characters.")
        salt = secrets.token_bytes(16)
        digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
        password_hash = f"scrypt$16384$8$1${salt.hex()}${digest.hex()}"
        return self._users.create(email, password_hash, display_name)

    def get(self, user_id: UUID) -> User:
        return self._users.get_by_id(user_id)

    def list(self, limit: int, offset: int) -> list[User]:
        if not 1 <= limit <= 100 or offset < 0:
            raise ErrInvalidInput("Limit must be 1 to 100 and offset must be non-negative.")
        return self._users.list(limit, offset)

    def update(self, user_id: UUID, email: str, display_name: str) -> User:
        email, display_name = self._validate(email, display_name)
        return self._users.update(user_id, email, display_name)

    def delete(self, user_id: UUID) -> None:
        self._users.delete(user_id)
