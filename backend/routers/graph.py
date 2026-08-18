from collections import defaultdict

from fastapi import APIRouter

from database import run_read

router = APIRouter(tags=["Graphe"])


@router.get("/graph")
def get_graph(personne: str):
    cypher = """
    MATCH (p:Personne {nom: $personne})
          -[r:COMPETENCE]->(c:Contexte)
          -[:CTX_TECHNO]->(t:Techno)

WITH t.nom AS techno,
     r.niveau AS niveau,
     split(c.cle, "|") AS parts

RETURN techno,
       niveau,
       parts[1] AS domaine
    """

    result = run_read(cypher, {"personne": personne})

    techno_map = defaultdict(list)
    for row in result:
        techno_map[row["techno"]].append({
            "niveau": row["niveau"],
            "domaine": row["domaine"]
        })

    nodes = []
    edges = []
    node_ids = {}
    current_id = 1

    def get_id(name):
        nonlocal current_id
        if name not in node_ids:
            node_ids[name] = current_id
            nodes.append({
                "id": current_id,
                "label": name
            })
            current_id += 1
        return node_ids[name]

    p_id = get_id(personne)

    for techno, details in techno_map.items():
        t_id = get_id(techno)
        tooltip_lines = [f"{d['domaine']} : N{d['niveau']}" for d in details]

        edges.append({
            "from": p_id,
            "to": t_id,
            "details": details,
            "title": "\n".join(tooltip_lines)
        })

    return {
        "nodes": nodes,
        "edges": edges
    }
