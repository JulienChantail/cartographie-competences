from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from database import run_read, run_write
from models import (
    CompetenceDelete,
    CompetenceOut,
    CompetenceRequest,
    CompetenceUpsert,
    PersonCreate,
    PersonDeleteRequest,
    RefItem,
)
from utils import get_user, make_cle

router = APIRouter(prefix="/personnes", tags=["Personnes"])


@router.get("", response_model=List[RefItem])
def list_personnes():
    cypher = "MATCH (p:Personne) RETURN p.nom AS nom ORDER BY nom"
    return run_read(cypher)


@router.post("")
def create_personne(payload: PersonCreate, x_user: str = Depends(get_user)):
    cypher = """
    CREATE (a:AuditEvent {
      id: randomUUID(),
      type: "PERSON_CREATE",
      auteur: $auteur,
      createdAt: datetime(),
      status: "PROPOSED",

      personne: $nom
    })

    RETURN "request_created" AS status
    """

    run_write(cypher, {
        "nom": payload.nom.strip(),
        "auteur": x_user
    })

    return {"status": "request_created"}


@router.post("/{nom}/competences/demandes")
def create_competence_request(
    nom: str,
    payload: CompetenceRequest,
    x_user: str = Depends(get_user),
):
    """
    Crée une DEMANDE de modification / création de compétence.
    Ne modifie PAS la relation COMPETENCE.
    Compatible si la personne n'existe pas encore.
    """
    cle = make_cle(payload.techno, payload.domaine, payload.version)

    cypher = """
    OPTIONAL MATCH (p:Personne {nom: $personneNom})

    MATCH (t:Techno {nom: $techno})
    MERGE (d:Domaine {nom: $domaine})
    MERGE (v:Version {nom: $version})

    WITH p, t, d, v, $cle AS cle

    MERGE (c:Contexte {cle: cle})
      ON CREATE SET c.createdAt = datetime()
    MERGE (c)-[:CTX_TECHNO]->(t)
    MERGE (c)-[:CTX_DOMAINE]->(d)
    MERGE (c)-[:CTX_VERSION]->(v)

    OPTIONAL MATCH (p)-[old:COMPETENCE]->(c)

    CREATE (a:AuditEvent {
        id: randomUUID(),
        type: "COMPETENCE_REQUEST",
        auteur: $auteur,
        createdAt: datetime(),
        status: "PROPOSED",

        personne: $personneNom,
        techno: $techno,
        domaine: $domaine,
        version: $version,

        cle_contexte: $cle,

        before_niveau: old.niveau,
        before_actif: old.actif,
        before_description: old.description,

        after_niveau: $niveau,
        after_actif: false,
        after_description: $description,
        demande_suppression: $demande_suppression
    })

    MERGE (a)-[:AUDIT_CTX]->(c)

    FOREACH (_ IN CASE WHEN p IS NOT NULL THEN [1] ELSE [] END |
        MERGE (a)-[:AUDIT_OF]->(p)
    )

    RETURN "request_created" AS status
    """

    rows = run_write(cypher, {
        "personneNom": nom,
        "auteur": x_user,
        "techno": payload.techno,
        "domaine": payload.domaine,
        "version": payload.version,
        "cle": cle,
        "niveau": payload.niveau,
        "description": payload.description,
        "demande_suppression": payload.demande_suppression
    })

    if not rows:
        raise HTTPException(status_code=404, detail="Personne ou référentiel introuvable")

    return {"status": "request_created"}


@router.post("/{nom}/suppression")
def create_person_delete_request(
    nom: str,
    payload: PersonDeleteRequest = PersonDeleteRequest(),
    x_user: str = Depends(get_user),
):
    """
    Crée une DEMANDE de suppression de personne, à valider par un manager.
    Ne supprime PAS la personne (voir DELETE /{nom} pour la suppression directe).
    """
    cypher = """
    MATCH (p:Personne {nom: $nom})
    CREATE (a:AuditEvent {
        id: randomUUID(),
        type: "PERSON_DELETE",
        auteur: $auteur,
        createdAt: datetime(),
        status: "PROPOSED",

        personne: $nom,
        after_description: $raison
    })
    MERGE (a)-[:AUDIT_OF]->(p)
    RETURN "request_created" AS status
    """

    rows = run_write(cypher, {
        "nom": nom,
        "auteur": x_user,
        "raison": payload.raison,
    })

    if not rows:
        raise HTTPException(status_code=404, detail="Personne introuvable")

    return {"status": "request_created"}


@router.delete("/{nom}")
def delete_personne(nom: str = Path(...)):
    cypher = """
    MATCH (p:Personne {nom: $nom})
    DETACH DELETE p
    RETURN $nom AS deleted
    """
    rows = run_write(cypher, {"nom": nom})
    if not rows:
        raise HTTPException(status_code=404, detail="Personne introuvable.")
    return {"deleted": rows[0]["deleted"]}


@router.get("/{nom}/competences", response_model=List[CompetenceOut])
def get_person_competences(
    nom: str = Path(...),
    techno: Optional[str] = Query(None),
    domaine: Optional[str] = Query(None),
    version: Optional[str] = Query(None),
):
    """Renvoie les compétences réelles d'une personne."""
    cypher = """
    MATCH (p:Personne {nom: $nom})-[r:COMPETENCE]->(c:Contexte)
    MATCH (c)-[:CTX_TECHNO]->(t:Techno)
    MATCH (c)-[:CTX_DOMAINE]->(d:Domaine)
    MATCH (c)-[:CTX_VERSION]->(v:Version)
    WHERE ($techno IS NULL OR t.nom = $techno)
      AND ($domaine IS NULL OR d.nom = $domaine)
      AND ($version IS NULL OR v.nom = $version)
    RETURN
      c.cle AS cle,
      t.nom AS techno,
      d.nom AS domaine,
      v.nom AS version,
      r.niveau AS niveau,
      coalesce(r.actif, true) AS actif,
      r.description AS description,
      toString(r.updatedAt) AS updatedAt,
      toString(r.createdAt) AS createdAt
    ORDER BY techno, domaine, version
    """
    return run_read(cypher, {
        "nom": nom,
        "techno": techno,
        "domaine": domaine,
        "version": version,
    })


@router.put("/{nom}/competences", response_model=CompetenceOut)
def upsert_person_competence(nom: str, payload: CompetenceUpsert):
    """
    Upsert d'une compétence VALIDÉE :
    - MERGE du Contexte (création si nécessaire)
    - SET du niveau / actif / description
    - Ne crée PAS d'AuditEvent ici (évite les doublons avec les demandes)
    """
    cle = make_cle(payload.techno, payload.domaine, payload.version)

    cypher = """
    MATCH (p:Personne {nom: $personneNom})
    MATCH (t:Techno {nom: $techno})
    MATCH (d:Domaine {nom: $domaine})
    MATCH (v:Version {nom: $version})

    WITH p,t,d,v, $cle AS cle

    MERGE (c:Contexte {cle: cle})
      ON CREATE SET c.createdAt = datetime()

    MERGE (c)-[:CTX_TECHNO]->(t)
    MERGE (c)-[:CTX_DOMAINE]->(d)
    MERGE (c)-[:CTX_VERSION]->(v)

    OPTIONAL MATCH (p)-[old:COMPETENCE]->(c)

    MERGE (p)-[r:COMPETENCE]->(c)
      ON CREATE SET r.createdAt = datetime()

    SET r.niveau = $niveau,
        r.actif = $actif,
        r.description = $description,
        r.updatedAt = datetime()

    MERGE (p)-[:MAITRISE]->(t)

    RETURN
      c.cle AS cle,
      t.nom AS techno,
      d.nom AS domaine,
      v.nom AS version,
      r.niveau AS niveau,
      coalesce(r.actif, true) AS actif,
      r.description AS description,
      toString(r.updatedAt) AS updatedAt,
      toString(r.createdAt) AS createdAt
    """

    rows = run_write(cypher, {
        "personneNom": nom,
        "techno": payload.techno,
        "domaine": payload.domaine,
        "version": payload.version,
        "cle": cle,
        "niveau": payload.niveau,
        "actif": payload.actif,
        "description": payload.description
    })

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Introuvable. Vérifie la personne et les référentiels (techno/domaine/version)."
        )

    return rows[0]


@router.delete("/{nom}/competences")
def delete_person_competence(
    nom: str,
    payload: CompetenceDelete,
    x_user: str = Depends(get_user),
):
    cle = make_cle(payload.techno, payload.domaine, payload.version)

    cypher = """
    MATCH (p:Personne {nom: $personneNom})
          -[r:COMPETENCE]->(c:Contexte {cle: $cle})

    CREATE (a:AuditEvent {
        id: randomUUID(),
        type: "COMPETENCE_DELETE",
        auteur: $auteur,
        createdAt: datetime(),
        status: "REJECTED",

        personne: $personneNom,
        techno: $techno,
        domaine: $domaine,
        version: $version,

        cle_contexte: $cle,

        before_niveau: r.niveau,
        before_actif: r.actif,
        before_description: r.description,

        after_niveau: null,
        after_actif: null,
        after_description: null
    })

    MERGE (a)-[:AUDIT_OF]->(p)
    MERGE (a)-[:AUDIT_CTX]->(c)

    DELETE r

    RETURN
      $personneNom AS personne,
      $cle AS cle
    """

    rows = run_write(cypher, {
        "personneNom": nom,
        "auteur": x_user,
        "techno": payload.techno,
        "domaine": payload.domaine,
        "version": payload.version,
        "cle": cle,
    })

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Compétence introuvable (rien à supprimer)."
        )

    return {
        "status": "deleted",
        "personne": rows[0]["personne"],
        "cle": rows[0]["cle"],
    }


@router.get("/{nom}/demandes")
def get_pending_requests_for_person(nom: str):
    cypher = """
    MATCH (a:AuditEvent {type: "COMPETENCE_REQUEST", status: "PROPOSED"})
    MATCH (a)-[:AUDIT_OF]->(p:Personne {nom: $nom})
    MATCH (a)-[:AUDIT_CTX]->(c:Contexte)
    MATCH (c)-[:CTX_TECHNO]->(t:Techno)
    MATCH (c)-[:CTX_DOMAINE]->(d:Domaine)
    MATCH (c)-[:CTX_VERSION]->(v:Version)

    RETURN
      t.nom AS techno,
      d.nom AS domaine,
      v.nom AS version,
      a.after_niveau AS niveau,
      a.after_description AS description
    """

    return run_read(cypher, {"nom": nom})
