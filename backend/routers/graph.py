from collections import defaultdict

from fastapi import APIRouter

from database import run_read

router = APIRouter(tags=["Graphe"])


def _build_graph(rows, person_names):
    """
    Construit {nodes, edges} au format vis-network à partir de lignes
    (personne, techno, niveau, domaine, categorie), pour une ou plusieurs
    personnes. `person_names` fixe l'ordre/l'ensemble des nœuds "personne"
    à créer même sans compétence (cas d'une personne isolée).
    """
    edge_map = defaultdict(list)
    techno_categories = {}
    for row in rows:
        edge_map[(row["personne"], row["techno"])].append({
            "niveau": row["niveau"],
            "domaine": row["domaine"]
        })
        techno_categories[row["techno"]] = row.get("categorie")

    nodes = []
    node_ids = {}
    current_id = 1

    def get_id(name, node_type, category=None):
        nonlocal current_id
        if name not in node_ids:
            node_ids[name] = current_id
            node = {"id": current_id, "label": name, "type": node_type}
            if category:
                node["category"] = category
            nodes.append(node)
            current_id += 1
        return node_ids[name]

    for personne in person_names:
        get_id(personne, "personne")

    edges = []
    for (personne, techno), details in edge_map.items():
        p_id = get_id(personne, "personne")
        t_id = get_id(techno, "techno", techno_categories.get(techno))
        tooltip_lines = [f"{d['domaine']} : N{d['niveau']}" for d in details]

        edges.append({
            "from": p_id,
            "to": t_id,
            "details": details,
            "title": "\n".join(tooltip_lines)
        })

    return {"nodes": nodes, "edges": edges}


@router.get("/graph")
def get_graph(personne: str):
    cypher = """
    MATCH (p:Personne {nom: $personne})
          -[r:COMPETENCE]->(c:Contexte)
          -[:CTX_TECHNO]->(t:Techno)
    WHERE coalesce(r.actif, true)
    OPTIONAL MATCH (t)-[:APPARTIENT_A]->(cat:TechnoCategory)

WITH p.nom AS personne,
     t.nom AS techno,
     cat.nom AS categorie,
     r.niveau AS niveau,
     split(c.cle, "|") AS parts

RETURN personne,
       techno,
       categorie,
       niveau,
       parts[1] AS domaine
    """

    result = run_read(cypher, {"personne": personne})
    return _build_graph(result, [personne])


@router.get("/graph/global")
def get_graph_global():
    """
    Vue d'ensemble : toutes les personnes et technologies reliées par au
    moins une compétence active, pour la vue "aucune personne sélectionnée"
    de profils.html.
    """
    cypher = """
    MATCH (p:Personne)-[r:COMPETENCE]->(c:Contexte)-[:CTX_TECHNO]->(t:Techno)
    WHERE coalesce(r.actif, true)
    OPTIONAL MATCH (t)-[:APPARTIENT_A]->(cat:TechnoCategory)

WITH p.nom AS personne,
     t.nom AS techno,
     cat.nom AS categorie,
     r.niveau AS niveau,
     split(c.cle, "|") AS parts

RETURN personne,
       techno,
       categorie,
       niveau,
       parts[1] AS domaine
    """

    result = run_read(cypher)
    person_names = sorted({row["personne"] for row in result})
    return _build_graph(result, person_names)
