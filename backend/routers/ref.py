from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from database import run_read, run_write
from models import RefItem, TechnoCreate
from utils import get_user

router = APIRouter(prefix="/ref", tags=["Référentiels"])


@router.get("/technos", response_model=List[RefItem])
def list_technos(category: Optional[str] = Query(None)):
    if category:
        cypher = """
        MATCH (t:Techno)-[:APPARTIENT_A]->(c:TechnoCategory {nom: $category})
        RETURN t.nom AS nom
        ORDER BY nom
        """
        return run_read(cypher, {"category": category})

    cypher = """
    MATCH (t:Techno)
    RETURN t.nom AS nom
    ORDER BY nom
    """
    return run_read(cypher)


@router.post("/technos")
def create_techno(payload: TechnoCreate, x_user: str = Depends(get_user)):
    cypher = """
    CREATE (a:AuditEvent {
      id: randomUUID(),
      type: "TECHNO_CREATE",
      auteur: $auteur,
      createdAt: datetime(),
      status: "PROPOSED",

      techno: $nom,
      category: $category,
      typeTechno: $type
    })

    RETURN "request_created" AS status
    """

    run_write(cypher, {
        "nom": payload.nom.strip(),
        "category": payload.category.strip(),
        "type": payload.type.strip(),
        "auteur": x_user
    })

    return {"status": "request_created"}


@router.get("/domaines", response_model=List[RefItem])
def list_domaines():
    cypher = "MATCH (d:Domaine) RETURN d.nom AS nom ORDER BY nom"
    return run_read(cypher)


@router.get("/versions", response_model=List[RefItem])
def list_versions():
    cypher = "MATCH (v:Version) RETURN v.nom AS nom ORDER BY nom"
    return run_read(cypher)


@router.get("/niveaux", response_model=List[int])
def list_niveaux():
    return [1, 2, 3]


@router.post("/domaines", response_model=RefItem)
def create_domaine(payload: RefItem):
    cypher = """
    MERGE (d:Domaine {nom: $nom})
    RETURN d.nom AS nom
    """
    rows = run_write(cypher, payload.model_dump())
    return rows[0]


@router.post("/versions", response_model=RefItem)
def create_version(payload: RefItem):
    cypher = """
    MERGE (v:Version {nom: $nom})
    RETURN v.nom AS nom
    """
    rows = run_write(cypher, payload.model_dump())
    return rows[0]


@router.get("/techno-categories", response_model=List[RefItem])
def list_techno_categories():
    cypher = """
    MATCH (c:TechnoCategory)
    RETURN c.nom AS nom
    ORDER BY nom
    """
    return run_read(cypher)
