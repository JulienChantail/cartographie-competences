
import os
from typing import List, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from jose import jwt, JWTError

# ==========================================================
# MODE DEV / PROD (feature flag)
# ==========================================================
#
# DEV_AUTH=true  → bypass complet de l'auth (POC)
# DEV_AUTH=false → JWT/SSO obligatoire (production)
#
DEV_AUTH = os.getenv("DEV_AUTH", "true").lower() == "true"

# ==========================================================
# Configuration JWT (future SSO / OIDC)
# ==========================================================

JWT_SECRET = os.getenv("JWT_SECRET", "DEV_SECRET_CHANGE_ME")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Claims courantes OIDC / JWT
CLAIM_USERNAME = "preferred_username"
CLAIM_EMAIL = "email"
CLAIM_ROLES = "roles"   # ex: ["user", "manager"]

# ==========================================================
# Modèle utilisateur interne
# ==========================================================

class CurrentUser(BaseModel):
    username: str
    email: Optional[str] = None
    roles: List[str] = []

# ==========================================================
# Dépendance FastAPI : Bearer token
# ==========================================================

security = HTTPBearer(auto_error=False)

# ==========================================================
# Authentification principale
# ==========================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    """
    Retourne l'utilisateur courant.

    - ✅ DEV_AUTH = true  → utilisateur simulé (pas de token requis)
    - 🔐 DEV_AUTH = false → validation JWT obligatoire
    """

    # ======================================================
    # ✅ MODE DEV / POC — BYPASS TOTAL DE L'AUTH
    # ======================================================
    if DEV_AUTH:
        return CurrentUser(
            username="poc.manager",
            email="poc.manager@local",
            roles=["user", "manager"]
        )

    # ======================================================
    # 🔐 MODE PROD — JWT STRICT
    # ======================================================
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"verify_aud": False},
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )

    # ======================================================
    # Extraction identité utilisateur
    # ======================================================
    username = (
        payload.get(CLAIM_USERNAME)
        or payload.get("sub")
        or payload.get("upn")
    )

    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token without user identity",
        )

    email = payload.get(CLAIM_EMAIL)

    roles = payload.get(CLAIM_ROLES, [])
    if isinstance(roles, str):
        roles = [roles]

    return CurrentUser(
        username=username,
        email=email,
        roles=roles,
    )

# ==========================================================
# Autorisation par rôle
# ==========================================================

def require_manager(user: CurrentUser):
    """
    Vérifie que l'utilisateur a le rôle 'manager'.

    En DEV_AUTH: cette fonction NE BLOQUE JAMAIS.
    """
    if DEV_AUTH:
        return

    if "manager" not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager role required",
        )
