import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import query as query_router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(query_router.router, prefix="/query")
    return TestClient(app)


def test_query_success(client, monkeypatch):
    def mock_invoke(state):
        return {
            **state,
            "final_answer": "This is the final legal answer.",
            "document_text": "Some extracted document text",
            "anon_knowledge": ["chunk1", "chunk2"],
            "detected_topic": ["contract law"],
            "confidence_delta": 0.87,
            "document_urls": ["https://example.com/doc1"],
        }

    monkeypatch.setattr(query_router.legal_graph, "invoke", mock_invoke)

    payload = {
        "user_id": "user-123",
        "query": "What are the termination clauses?",
    }

    response = client.post("/query", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "This is the final legal answer."
    assert data["has_document_context"] is True
    assert data["has_knowledge_context"] is True
    assert data["detected_topic"] == ["contract law"]
    assert data["confidence_delta"] == 0.87
    assert data["document_urls"] == ["https://example.com/doc1"]


def test_query_empty_query_returns_400(client):
    payload = {
        "user_id": "user-123",
        "query": "   ",
    }

    response = client.post("/query", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "Query cannot be empty."


def test_query_graph_failure_returns_500(client, monkeypatch):
    def mock_invoke(state):
        raise RuntimeError("Something blew up in the graph")

    monkeypatch.setattr(query_router.legal_graph, "invoke", mock_invoke)

    payload = {
        "user_id": "user-123",
        "query": "Summarize this contract",
    }

    response = client.post("/query", json=payload)

    assert response.status_code == 500
    assert "Graph execution failed: Something blew up in the graph" in response.json()["detail"]