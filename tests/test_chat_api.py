from pathlib import Path
import sys
import types

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from webapp import create_app
from webapp.extensions import db


@pytest.fixture()
def app(tmp_path):
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
        }
    )
    yield application
    with application.app_context():
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def signup_and_login(client, name, email):
    client.post("/signup", data={"name": name, "email": email, "password": "passphrase"})
    response = client.post("/login", data={"email": email, "password": "passphrase"})
    assert response.status_code == 302


def test_chat_requires_login(client):
    response = client.post("/api/chat", json={"message": "What is civil engineering?"})
    assert response.status_code == 401


def test_chat_persists_only_for_authenticated_user(app, client, monkeypatch):
    fake_engine = types.ModuleType("webapp.services.chatbot_engine")
    fake_engine.reply = lambda question: "TensorFlow fallback reply"
    monkeypatch.setitem(sys.modules, "webapp.services.chatbot_engine", fake_engine)
    monkeypatch.setattr("webapp.routes.record_question", lambda question: None)
    signup_and_login(client, "First User", "first@example.com")

    response = client.post("/api/chat", json={"message": "What is civil engineering?"})
    assert response.status_code == 200
    assert response.get_json() == {"answer": "TensorFlow fallback reply"}
    assert client.get("/api/history").get_json()["dates"]

    client.post("/logout")
    signup_and_login(client, "Second User", "second@example.com")
    assert client.get("/api/history").get_json() == {"dates": []}
