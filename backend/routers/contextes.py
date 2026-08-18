from typing import List, Optional

from fastapi import APIRouter, HTTPException, Path, Query

from database import run_read, run_write
from models import ContexteKey, ContexteOut
from utils import make_cle

router = APIRouter(prefix="/contextes", tags=["Contextes"])


@router.post("", response_model=ContexteOut)
def upsert_contexte(payload: ContexteKey):
    """
    Crée (ou récupère) un Contexte unique = techno|domaine|version,
    et le relie aux nœuds existants Techno/Domaine/Version.
    """
    cle = make_cle(payload.techno, payload.domaine, payload.version)

    cypher = """
    MATCH (t:Techno {nom: $techno})
    MATCH (d:Domaine {nom: $domaine})
    MATCH (v:Version {nom: $version})
    WITH t,d,v, $cle AS cle
    MERGE (c:Contexte {cle: cle})
      ON CREATE SET c.createdAt = datetime()
    MERGE (c)-[:CTX_TECHNO]->(t)
    MERGE (c)-[:CTX_DOMAINE]->(d)
    MERGE (c)-[:CTX_VERSION]->(v)
    RETURN
      c.cle AS cle,
      t.nom AS techno,
      d.nom AS domaine,
      v.nom AS version
    """
    rows = run_write(cypher, {
        "techno": payload.techno,
        "domaine": payload.domaine,
        "version": payload.version,
        "cle": cle
    })
    if not rows:
        raise HTTPException(status_code=404, detail="Référentiel introuvable (techno/domaine/version). Crée-les d'abord.")
    return rows[0]


@router.get("", response_model=List[ContexteOut])
def list_contextes(
    category: Optional[str] = Query(None),
    techno: Optional[str] = Query(None),
    domaine: Optional[str] = Query(None),
    version: Optional[str] = Query(None),
):
    cypher = """
MATCH (c:Contexte)-[:CTX_TECHNO]->(t:Techno)
MATCH (t)-[:APPARTIENT_A]->(cat:TechnoCategory)
MATCH (c)-[:CTX_DOMAINE]->(d:Domaine)
MATCH (c)-[:CTX_VERSION]->(v:Version)

WHERE ($category IS NULL OR cat.nom = $category)
  AND ($techno IS NULL OR t.nom = $techno)
  AND ($domaine IS NULL OR d.nom = $domaine)
  AND ($version IS NULL OR v.nom = $version)

RETURN
  c.cle AS cle,
  t.nom AS techno,
  d.nom AS domaine,
  v.nom AS version

ORDER BY techno, domaine, version
"""

    return run_read(cypher, {
        "category": category,
        "techno": techno,
        "domaine": domaine,
        "version": version
    })


@router.delete("/{cle}")
def delete_contexte_if_unused(cle: str = Path(..., description="Clé du contexte techno|domaine|version")):
    """Supprime un contexte uniquement s'il n'est utilisé par aucune compétence."""
    cypher = """
    MATCH (c:Contexte {cle: $cle})
    OPTIONAL MATCH (c)<-[r:COMPETENCE]-(:Personne)
    WITH c, count(r) AS nb
    WHERE nb = 0
    DETACH DELETE c
    RETURN $cle AS cle, nb AS nbCompetences
    """
    rows = run_write(cypher, {"cle": cle})
    if not rows:
        exists_rows = run_read("MATCH (c:Contexte {cle:$cle}) RETURN c.cle AS cle", {"cle": cle})
        if not exists_rows:
            raise HTTPException(status_code=404, detail="Contexte introuvable.")
        raise HTTPException(status_code=409, detail="Contexte utilisé par des compétences, suppression refusée.")
    return {"status": "deleted_if_unused", "cle": rows[0]["cle"], "nbCompetences": rows[0]["nbCompetences"]}
