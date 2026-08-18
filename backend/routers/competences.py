from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

from database import run_read

router = APIRouter(prefix="/competences", tags=["Compétences"])


@router.get("/contexte", response_model=List[Dict[str, Any]])
def list_competences_for_contexte(
    category: Optional[str] = Query(None),
    techno: Optional[str] = Query(None),
    domaine: Optional[str] = Query(None),
    version: Optional[str] = Query(None),
):
    """Vue "qui a quoi" sur un contexte donné (utile côté UI admin)."""

    def nullify(v: Optional[str]) -> Optional[str]:
        return v if v and v.strip() != "" else None

    cypher = """
MATCH (p:Personne)-[r:COMPETENCE]->(c:Contexte)
MATCH (c)-[:CTX_TECHNO]->(t:Techno)
MATCH (t)-[:APPARTIENT_A]->(cat:TechnoCategory)
MATCH (c)-[:CTX_DOMAINE]->(d:Domaine)
MATCH (c)-[:CTX_VERSION]->(v:Version)
WHERE ($techno IS NULL OR t.nom = $techno)
  AND ($category IS NULL OR cat.nom = $category)
  AND ($domaine IS NULL OR d.nom = $domaine)
  AND ($version IS NULL OR v.nom = $version)
RETURN
  p.nom AS personne,
  t.nom AS techno,
  cat.nom AS category,
  d.nom AS domaine,
  v.nom AS version,
  r.niveau AS niveau,
  coalesce(r.actif, true) AS actif,
  r.description AS description,
  toString(r.updatedAt) AS updatedAt
ORDER BY personne
    """

    return run_read(cypher, {
        "techno": nullify(techno),
        "category": nullify(category),
        "domaine": nullify(domaine),
        "version": nullify(version),
    })
