from typing import List, Optional

from fastapi import APIRouter, Header, HTTPException

from auth_deps import count_active_admins, require_admin
from database import run_read, run_write
from models import UserCreate, UserOut, UserRoleUpdate
from utils import validate_capgemini_email

router = APIRouter(prefix="/users", tags=["Utilisateurs"])


@router.get("", response_model=List[UserOut])
def list_users(x_user: Optional[str] = Header(None)):
    require_admin(x_user)

    cypher = """
    MATCH (u:User)
    RETURN
      u.email AS email,
      u.role AS role,
      coalesce(u.active, true) AS active
    ORDER BY email
    """

    return run_read(cypher)


@router.post("", response_model=UserOut)
def create_user(payload: UserCreate, x_user: Optional[str] = Header(None)):
    admin = require_admin(x_user)

    email = validate_capgemini_email(payload.email)

    if not payload.password or not payload.password.strip():
        raise HTTPException(400, "Mot de passe obligatoire")

    exists = run_read("""
        MATCH (u:User {email: $email})
        RETURN u.email AS email
    """, {"email": email})

    if exists:
        raise HTTPException(
            status_code=409,
            detail="Un utilisateur avec cet email existe déjà"
        )

    rows = run_write("""
        CREATE (u:User {
          email: $email,
          password: $password,
          role: $role,
          active: true,
          createdAt: datetime(),
          createdBy: $createdBy
        })
        RETURN
          u.email AS email,
          u.role AS role,
          coalesce(u.active, true) AS active
    """, {
        "email": email,
        "password": payload.password,
        "role": payload.role,
        "createdBy": admin["email"]
    })

    return rows[0]


@router.put("/{email}/role", response_model=UserOut)
def update_user_role(email: str, payload: UserRoleUpdate, x_user: Optional[str] = Header(None)):
    require_admin(x_user)

    email = validate_capgemini_email(email)
    new_role = payload.role

    rows = run_read("""
        MATCH (u:User {email: $email})
        RETURN
          u.email AS email,
          u.role AS role,
          coalesce(u.active, true) AS active
    """, {"email": email})

    if not rows:
        raise HTTPException(404, "Utilisateur introuvable")

    current = rows[0]

    if current["role"] == "ADMIN" and new_role == "USER":
        if count_active_admins() <= 1:
            raise HTTPException(
                status_code=409,
                detail="Impossible de rétrograder le dernier administrateur"
            )

    updated = run_write("""
        MATCH (u:User {email: $email})
        SET
          u.role = $role,
          u.updatedAt = datetime()
        RETURN
          u.email AS email,
          u.role AS role,
          coalesce(u.active, true) AS active
    """, {
        "email": email,
        "role": new_role
    })

    return updated[0]


@router.delete("/{email}")
def delete_user(email: str, x_user: Optional[str] = Header(None)):
    require_admin(x_user)

    email = validate_capgemini_email(email)

    rows = run_read("""
        MATCH (u:User {email: $email})
        RETURN
          u.email AS email,
          u.role AS role,
          coalesce(u.active, true) AS active
    """, {"email": email})

    if not rows:
        raise HTTPException(404, "Utilisateur introuvable")

    target = rows[0]

    if target["role"] == "ADMIN" and target["active"] is True:
        if count_active_admins() <= 1:
            raise HTTPException(
                status_code=409,
                detail="Impossible de supprimer le dernier administrateur"
            )

    run_write("""
        MATCH (u:User {email: $email})
        DETACH DELETE u
        RETURN $email AS deleted
    """, {"email": email})

    return {
        "deleted": email
    }
