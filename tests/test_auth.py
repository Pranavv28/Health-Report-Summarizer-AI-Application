"""
tests/test_auth.py — Unit and integration tests for auth and memory system.
"""

import os
import pytest
import auth


@pytest.fixture(autouse=True)
def setup_teardown_db(tmp_path, monkeypatch):
    """Run tests against an isolated temporary database."""
    test_db = tmp_path / "test_users.db"
    monkeypatch.setattr(auth, "DB_PATH", test_db)
    auth.init_db()
    yield
    if test_db.exists():
        try:
            test_db.unlink()
        except Exception:
            pass


def test_user_creation_and_duplicate():
    res = auth.create_user("Alice Smith", "alice@example.com", "Password123!")
    assert res["ok"] is True
    assert res["user"]["name"] == "Alice Smith"
    assert res["user"]["email"] == "alice@example.com"
    assert res["user"]["id"] > 0

    # Duplicate should fail gracefully
    dup = auth.create_user("Alice Smith", "alice@example.com", "AnotherPassword!")
    assert dup["ok"] is False
    assert "already exists" in dup["error"]


def test_authenticate_user():
    auth.create_user("Bob Jones", "bob@example.com", "SecretPass456!")

    # Correct credentials
    user = auth.authenticate_user("bob@example.com", "SecretPass456!")
    assert user is not None
    assert user["name"] == "Bob Jones"
    assert user["email"] == "bob@example.com"

    # Case insensitivity in email
    user_ci = auth.authenticate_user("BOB@EXAMPLE.COM", "SecretPass456!")
    assert user_ci is not None

    # Incorrect password
    assert auth.authenticate_user("bob@example.com", "WrongPassword") is None

    # Non-existent user
    assert auth.authenticate_user("ghost@example.com", "AnyPassword") is None


def test_jwt_token_cycle():
    user_id = 42
    email = "charlie@example.com"
    name = "Charlie Brown"

    token = auth.create_jwt(user_id, email, name)
    assert isinstance(token, str)
    assert len(token) > 20

    # Valid token verification
    payload = auth.verify_jwt(token)
    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["email"] == email
    assert payload["name"] == name

    # Tampered / invalid token
    assert auth.verify_jwt("tampered.token.value") is None
    assert auth.verify_jwt("") is None


def test_report_memory_crud():
    user_res = auth.create_user("Dana White", "dana@example.com", "DanaPassword123!")
    uid = user_res["user"]["id"]

    # Initial history is empty
    assert auth.get_report_history(uid) == []

    # Save first report
    rep1_id = auth.save_report(uid, "CBC Test", '{"biomarkers": []}', findings_count=4)
    assert rep1_id > 0

    # Save second report
    rep2_id = auth.save_report(uid, "Metabolic Panel", '{"biomarkers": []}', findings_count=2)
    assert rep2_id > 0

    # Fetch history - newest first
    history = auth.get_report_history(uid)
    assert len(history) == 2
    assert history[0]["id"] == rep2_id
    assert history[0]["title"] == "Metabolic Panel"
    assert history[1]["id"] == rep1_id

    # Fetch by ID
    rec = auth.get_report_by_id(rep1_id, uid)
    assert rec is not None
    assert rec["title"] == "CBC Test"
    assert "biomarkers" in rec["summary_json"]

    # Delete report
    deleted = auth.delete_report(rep1_id, uid)
    assert deleted is True
    history_after = auth.get_report_history(uid)
    assert len(history_after) == 1
    assert history_after[0]["id"] == rep2_id

    # Deleting nonexistent or wrong user returns False
    assert auth.delete_report(rep1_id, uid) is False
    assert auth.delete_report(rep2_id, uid + 999) is False
