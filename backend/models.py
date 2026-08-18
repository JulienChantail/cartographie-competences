from typing import List, Literal, Optional

from pydantic import BaseModel, Field, conint

NiveauType = conint(ge=1, le=3)


class PersonCreate(BaseModel):
    nom: str


class PersonDeleteRequest(BaseModel):
    raison: Optional[str] = None


class RefItem(BaseModel):
    nom: str


class TechnoCreate(BaseModel):
    nom: str
    category: str
    type: str


class ContexteKey(BaseModel):
    techno: str = Field(..., description="Nom de la techno (ex: MongoDB)")
    domaine: str = Field(..., description="Nom du domaine (Run MCO/Build/Architecture)")
    version: str = Field(..., description="Nom de la version (ex: MongoDB 6)")


class ContexteOut(BaseModel):
    cle: str
    techno: str
    domaine: str
    version: str


class CompetenceUpsert(BaseModel):
    techno: str
    domaine: str
    version: str
    niveau: NiveauType
    actif: bool = True
    description: Optional[str] = None


class CompetenceOut(BaseModel):
    cle: str
    techno: str
    domaine: str
    version: str
    niveau: int
    actif: bool
    description: Optional[str] = None
    updatedAt: Optional[str] = None
    createdAt: Optional[str] = None


class CompetenceDelete(BaseModel):
    techno: str
    domaine: str
    version: str


class CompetenceRequest(BaseModel):
    techno: str
    domaine: str
    version: str
    niveau: NiveauType
    description: Optional[str] = None


class DecisionPayload(BaseModel):
    decision: Literal["VALIDATED", "REJECTED"]
    comment: Optional[str] = None


class QuestionnaireRequest(BaseModel):
    personne: str
    competences: List[CompetenceRequest]


class LoginPayload(BaseModel):
    email: str
    password: str


class UserCreate(BaseModel):
    email: str
    password: str
    role: Literal["ADMIN", "USER"] = "USER"


class UserRoleUpdate(BaseModel):
    role: Literal["ADMIN", "USER"]


class UserOut(BaseModel):
    email: str
    role: str
    active: bool = True
