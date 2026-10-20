"""API tests.

Each test runs against a fresh in-memory SQLite database, so the suite is
fast and order-independent:  pytest -q
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# StaticPool keeps one shared connection, so the in-memory database
# (and its tables) is the same for every session in the test run.
engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    db = TestingSession()
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    db.close()


def make_application(**overrides):
    payload = {
        "company": "Stripe",
        "role": "Software Engineer, Early Career",
        "location": "San Francisco, CA",
        "status": "applied",
    }
    payload.update(overrides)
    response = client.post("/applications", json=payload)
    assert response.status_code == 201
    return response.json()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_get():
    created = make_application()
    assert created["company"] == "Stripe"
    assert created["status"] == "applied"

    fetched = client.get(f"/applications/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["role"] == "Software Engineer, Early Career"


def test_create_validation_error():
    response = client.post("/applications", json={"role": "No company given"})
    assert response.status_code == 422


def test_get_missing_returns_404():
    assert client.get("/applications/9999").status_code == 404


def test_list_filter_by_status_and_company():
    make_application(company="Stripe")
    make_application(company="Affirm", status="interview")
    make_application(company="affirmative", status="applied")

    applied = client.get("/applications", params={"status": "applied"}).json()
    assert applied["total"] == 2

    affirm = client.get("/applications", params={"company": "AFFIRM"}).json()
    assert affirm["total"] == 2  # case-insensitive substring match


def test_pagination():
    for i in range(5):
        make_application(company=f"Company {i}")
    page1 = client.get("/applications", params={"page": 1, "page_size": 2}).json()
    page3 = client.get("/applications", params={"page": 3, "page_size": 2}).json()
    assert page1["total"] == 5
    assert len(page1["items"]) == 2
    assert len(page3["items"]) == 1


def test_update_status_and_notes():
    created = make_application()
    updated = client.patch(
        f"/applications/{created['id']}",
        json={"status": "oa", "notes": "HackerRank, due Friday"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "oa"
    assert updated.json()["notes"] == "HackerRank, due Friday"


def test_update_missing_returns_404():
    assert client.patch("/applications/9999", json={"status": "oa"}).status_code == 404


def test_delete():
    created = make_application()
    assert client.delete(f"/applications/{created['id']}").status_code == 204
    assert client.get(f"/applications/{created['id']}").status_code == 404


def test_stats():
    make_application(status="applied")
    make_application(status="interview")
    make_application(status="rejected")
    data = client.get("/stats").json()
    assert data["total"] == 3
    assert data["by_status"]["interview"] == 1
    assert data["by_status"]["offer"] == 0
    assert data["applied_last_7_days"] == 3
    assert data["response_rate"] == pytest.approx(2 / 3, abs=0.01)
