import json

from fastapi import APIRouter, Depends

from database import run_write
from models import QuestionnaireRequest
from utils import get_user

router = APIRouter(tags=["Questionnaire"])


@router.post("/questionnaire")
def submit_questionnaire(
    payload: QuestionnaireRequest,
    x_user: str = Depends(get_user),
):
    cypher = """
    CREATE (a:AuditEvent {
      id: randomUUID(),
      type: "QUESTIONNAIRE_REQUEST",
      auteur: $auteur,
      createdAt: datetime(),
      status: "PROPOSED",

      personne: $personne,
      data: $data
    })
    RETURN "ok" AS status
    """

    run_write(cypher, {
        "auteur": x_user,
        "personne": payload.personne,
        "data": json.dumps(payload.model_dump()["competences"])
    })

    return {"status": "request_created"}
