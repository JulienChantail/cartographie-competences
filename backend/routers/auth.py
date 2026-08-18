from fastapi import APIRouter, HTTPException

from database import run_read
from models import LoginPayload, UserOut
from utils import validate_capgemini_email

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/login", response_model=UserOut)
def login(payload: LoginPayload):
    email = validate_capgemini_email(payload.email)

    rows = run_read("""
        MATCH (u:User {
          email: $email,
          password: $password,
          active: true
        })
        RETURN
          u.email AS email,
          u.role AS role,
          coalesce(u.active, true) AS active
    """, {
        "email": email,
        "password": payload.password
    })

    if not rows:
        raise HTTPException(
            status_code=401,
            detail="Email ou mot de passe incorrect"
        )

    return rows[0]
