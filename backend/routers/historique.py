import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from database import run_read, run_write
from models import DecisionPayload
from utils import empty_to_none, get_user

router = APIRouter(prefix="/historique", tags=["Historique"])


@router.get("", response_model=List[Dict[str, Any]])
def get_historique(
    personne: Optional[str] = Query(None),
    techno: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    limit: int = Query(100, le=500),
    x_user: str = Depends(get_user),
):
    # "" -> None, sinon aucun filtre ne matche
    personne = empty_to_none(personne)
    techno = empty_to_none(techno)
    status = empty_to_none(status)
    type = empty_to_none(type)

    cypher = """
MATCH (a:AuditEvent)

WHERE
  ($status IS NULL OR a.status = $status)
  AND ($type IS NULL OR a.type = $type)
  AND ($personne IS NULL OR a.personne = $personne)
  AND ($techno IS NULL OR a.techno = $techno)
  AND ($from_date IS NULL OR a.createdAt >= datetime($from_date))
  AND ($to_date IS NULL OR a.createdAt < datetime($to_date) + duration('P1D'))

RETURN {
  id: a.id,
  createdAt: toString(a.createdAt),
  auteur: a.auteur,
  personne: a.personne,
  techno: a.techno,
  domaine: a.domaine,
  version: a.version,
  type: a.type,
  status: a.status,
  manager: a.manager,
  decisionAt: toString(a.decisionAt),

  category: a.category,
  typeTechno: a.typeTechno,
  before_nom: a.before_nom,
  after_nom: a.after_nom,

  decisionComment: a.decisionComment,

  before: {
    niveau: a.before_niveau,
    description: a.before_description
  },

  after: {
    niveau: a.after_niveau,
    description: a.after_description
  }

} AS event

ORDER BY a.createdAt DESC
LIMIT $limit
    """

    rows = run_read(cypher, {
        "personne": personne,
        "techno": techno,
        "status": status,
        "type": type,
        "from_date": from_date,
        "to_date": to_date,
        "limit": limit,
    })

    return [r["event"] for r in rows]


@router.put("/{event_id}/decision")
def decide_competence_request(
    event_id: str,
    payload: DecisionPayload,
    x_user: str = Depends(get_user),
):
    manager = x_user.strip()
    decision = payload.decision
    comment = payload.comment

    if decision == "VALIDATED":
        event_data = run_read("""
            MATCH (a:AuditEvent {id: $id})
            RETURN a.type AS type,
                   a.personne AS personne,
                   a.data AS data
        """, {"id": event_id})

        if not event_data:
            raise HTTPException(404, "Demande introuvable")

        event_data = event_data[0]

        # Cas particulier : questionnaire global (plusieurs compétences d'un coup)
        if event_data["type"] == "QUESTIONNAIRE_REQUEST":
            personne = event_data["personne"]
            competences = json.loads(event_data.get("data") or "[]")

            run_write("MERGE (p:Personne {nom: $nom})", {"nom": personne})

            for c in competences:
                cle = f"{c['techno']}|{c['domaine']}|{c['version']}"

                run_write("""
                MERGE (t:Techno {nom: $techno})
                MERGE (d:Domaine {nom: $domaine})
                MERGE (v:Version {nom: $version})

                WITH t,d,v,$cle AS cle
                MERGE (ctx:Contexte {cle: cle})
                  ON CREATE SET ctx.createdAt = datetime()

                MERGE (ctx)-[:CTX_TECHNO]->(t)
                MERGE (ctx)-[:CTX_DOMAINE]->(d)
                MERGE (ctx)-[:CTX_VERSION]->(v)

                MERGE (p:Personne {nom: $personne})
                MERGE (p)-[r:COMPETENCE]->(ctx)
                  ON CREATE SET r.createdAt = datetime()

                SET r.niveau = $niveau,
                    r.actif = true,
                    r.updatedAt = datetime()
                """, {
                    "personne": personne,
                    "techno": c["techno"],
                    "domaine": c["domaine"],
                    "version": c["version"],
                    "niveau": c["niveau"],
                    "cle": cle
                })

            run_write("""
                MATCH (a:AuditEvent {id: $id})
                SET
                    a.status = "VALIDATED",
                    a.manager = $manager,
                    a.decisionAt = datetime(),
                    a.decisionComment = $comment
                RETURN 1
            """, {
                "id": event_id,
                "manager": manager,
                "comment": comment
            })

            return {
                "decision": decision,
                "closed_count": 1
            }

        # Cas standard : COMPETENCE_REQUEST / PERSON_CREATE / TECHNO_CREATE
        cypher = """
        MATCH (a:AuditEvent {id: $id})

        OPTIONAL MATCH (a)-[:AUDIT_CTX]->(c:Contexte)

        MERGE (p:Personne {nom: a.personne})

        WITH a, p, c
        OPTIONAL MATCH (p)-[r:COMPETENCE]->(c)

        WITH a, p, c, r

        FOREACH (_ IN CASE
            WHEN a.type = "COMPETENCE_REQUEST" AND r IS NOT NULL
            THEN [1] ELSE [] END |
            DELETE r
        )

        FOREACH (_ IN CASE
            WHEN a.type = "COMPETENCE_REQUEST"
              AND c IS NOT NULL
              AND NOT (a.after_description CONTAINS "suppression")
            THEN [1] ELSE [] END |

            MERGE (p)-[r2:COMPETENCE]->(c)
              ON CREATE SET r2.createdAt = datetime()
            SET
              r2.niveau = a.after_niveau,
              r2.actif = true,
              r2.description = a.after_description,
              r2.updatedAt = datetime()
        )

        FOREACH (_ IN CASE
          WHEN a.type = "TECHNO_CREATE" THEN [1] ELSE [] END |

          MERGE (t:Techno {nom: a.techno})
          SET t.type = a.typeTechno

          MERGE (cat:TechnoCategory {nom: a.category})
          MERGE (t)-[:APPARTIENT_A]->(cat)
        )

        FOREACH (_ IN CASE
          WHEN a.type = "PERSON_DELETE" THEN [1] ELSE [] END |
          DETACH DELETE p
        )

        SET
          a.status = "VALIDATED",
          a.manager = $manager,
          a.decisionAt = datetime(),
          a.decisionComment = $comment

        RETURN 1 AS closed_count
        """

    else:
        cypher = """
        MATCH (a:AuditEvent {id: $id})
        SET
          a.status = "REJECTED",
          a.manager = $manager,
          a.decisionAt = datetime(),
          a.decisionComment = $comment
        RETURN 1 AS closed_count
        """

    rows = run_write(cypher, {
        "id": event_id,
        "manager": manager,
        "comment": comment
    })

    if not rows:
        raise HTTPException(404, "Demande introuvable")

    return {
        "decision": decision,
        "closed_count": rows[0]["closed_count"]
    }
