from typing import List, Optional

from fastapi import APIRouter, Query

from database import run_read

router = APIRouter(prefix="/stats", tags=["Statistiques"])


@router.get("/niveau3-par-categorie")
def niveau3_par_categorie(category: Optional[List[str]] = Query(None)):
    """
    Pour chaque TechnoCategory demandée, nombre de personnes distinctes ayant
    au moins une compétence active de niveau 3 sur une techno de cette
    catégorie. Retourne 0 pour une catégorie sans résultat (pas d'omission).
    """
    categories = category or []

    cypher = """
    UNWIND $categories AS category
    OPTIONAL MATCH (p:Personne)-[r:COMPETENCE]->(:Contexte)
                    -[:CTX_TECHNO]->(:Techno)-[:APPARTIENT_A]->(cat:TechnoCategory {nom: category})
    WHERE r.niveau = 3 AND coalesce(r.actif, true)
    RETURN category, count(DISTINCT p) AS personnes
    """

    return run_read(cypher, {"categories": categories})
