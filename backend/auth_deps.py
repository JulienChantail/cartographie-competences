from typing import Any, Dict, Optional

from fastapi import HTTPException

from database import run_read
from utils import normalize_email


def get_current_user_record(x_user: Optional[str]) -> Dict[str, Any]:
    if not x_user:
        raise HTTPException(401, "Utilisateur requis")

    email = normalize_email(x_user)

    rows = run_read("""
        MATCH (u:User {email: $email, active: true})
        RETURN
          u.email AS email,
          u.role AS role,
          coalesce(u.active, true) AS active
    """, {"email": email})

    if not rows:
        raise HTTPException(401, "Utilisateur inconnu ou inactif")

    return rows[0]


def require_admin(x_user: Optional[str]) -> Dict[str, Any]:
    user = get_current_user_record(x_user)

    if user["role"] != "ADMIN":
        raise HTTPException(403, "Accès réservé aux administrateurs")

    return user


def count_active_admins() -> int:
    rows = run_read("""
        MATCH (u:User {role: "ADMIN", active: true})
        RETURN count(u) AS count
    """)

    return rows[0]["count"] if rows else 0
