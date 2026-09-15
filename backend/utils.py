import re
from typing import Optional

from fastapi import Header, HTTPException

CAPGEMINI_EMAIL_REGEX = re.compile(
    r"^[a-zA-Z]+(?:-[a-zA-Z]+)?\.[a-zA-Z]+(?:-[a-zA-Z]+)?(?:@capgemini\.com)?$"
)


def empty_to_none(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value if value else None


def make_cle(techno: str, domaine: str, version: str) -> str:
    return f"{techno}|{domaine}|{version}"


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def validate_capgemini_email(email: str) -> str:
    email = normalize_email(email)

    if email == "admin":
        return email

    if not CAPGEMINI_EMAIL_REGEX.match(email):
        raise HTTPException(
            status_code=400,
            detail="Email invalide. Format attendu : prenom.nom@capgemini.com"
        )

    return email


def get_user(x_user: Optional[str] = Header(None)) -> str:
    """Dependency FastAPI : exige la présence du header X-User (identité déclarée par le frontend)."""
    if not x_user:
        raise HTTPException(401, "Utilisateur requis")
    return x_user
