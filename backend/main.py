import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import database
from routers import auth, competences, contextes, graph, historique, personnes, questionnaire, ref, users

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "")

origins = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()]
if not origins:
    origins = [
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.connect()
    yield
    database.disconnect()


app = FastAPI(
    title="Skills Graph API",
    version="0.3.0",
    description=(
        "API FastAPI pour interagir avec Neo4j selon le modèle : "
        "Personne -[COMPETENCE]-> Contexte -(CTX_*)-> (Techno/Domaine/Version)."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ref.router)
app.include_router(personnes.router)
app.include_router(contextes.router)
app.include_router(competences.router)
app.include_router(historique.router)
app.include_router(graph.router)
app.include_router(questionnaire.router)
app.include_router(auth.router)
app.include_router(users.router)


@app.get("/health")
def health():
    rows = database.run_read("RETURN 1 AS ok")
    return {"ok": rows[0]["ok"] == 1, "neo4j_uri": database.NEO4J_URI}
