import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import HTTPException
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j")

driver = None


def connect() -> None:
    global driver
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()


def disconnect() -> None:
    global driver
    if driver:
        driver.close()
        driver = None


def run_read(cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    params = params or {}
    try:
        with driver.session() as session:
            result = session.run(cypher, params)
            return [record.data() for record in result]
    except Neo4jError as e:
        raise HTTPException(status_code=500, detail=f"Neo4j read error: {str(e)}")


def run_write(cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    params = params or {}
    try:
        with driver.session() as session:
            def work(tx):
                result = tx.run(cypher, params)
                records = list(result)
                result.consume()
                return [r.data() for r in records]

            return session.execute_write(work)
    except Neo4jError as e:
        raise HTTPException(status_code=500, detail=f"Neo4j write error: {str(e)}")
