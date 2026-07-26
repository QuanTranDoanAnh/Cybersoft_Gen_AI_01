import pytest
import psycopg

from app import database
from app.database import get_database_settings


def test_postgres_settings_use_five_environment_variables():
    settings = get_database_settings({
        "DB_HOST": "db.internal",
        "DB_PORT": "5432",
        "DB_USER": "orbit_user",
        "DB_PASS": "p@ss:word/with-special-characters",
        "DATABASE": "orbit",
    })

    assert settings.engine == "postgresql"
    assert settings.host == "db.internal"
    assert settings.port == 5432
    assert settings.user == "orbit_user"
    assert settings.password == "p@ss:word/with-special-characters"
    assert settings.database == "orbit"


def test_partial_postgres_settings_are_rejected():
    with pytest.raises(RuntimeError, match="DB_USER, DB_PASS, DATABASE"):
        get_database_settings({"DB_HOST": "localhost", "DB_PORT": "5432"})


def test_invalid_postgres_port_is_rejected():
    with pytest.raises(RuntimeError, match="DB_PORT"):
        get_database_settings({
            "DB_HOST": "localhost",
            "DB_PORT": "not-a-port",
            "DB_USER": "orbit",
            "DB_PASS": "secret",
            "DATABASE": "orbit",
        })


def test_sqlite_is_the_local_fallback(tmp_path):
    path = tmp_path / "test.db"
    settings = get_database_settings({"DATABASE_PATH": str(path)})

    assert settings.engine == "sqlite"
    assert settings.sqlite_path == path


def test_postgres_connection_passes_credentials_as_driver_arguments(monkeypatch):
    settings = get_database_settings({
        "DB_HOST": "db.internal",
        "DB_PORT": "5432",
        "DB_USER": "orbit_user",
        "DB_PASS": "p@ss:word/with-special-characters",
        "DATABASE": "orbit",
    })
    captured = {}
    expected_connection = object()

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return expected_connection

    monkeypatch.setattr(database, "SETTINGS", settings)
    monkeypatch.setattr(psycopg, "connect", fake_connect)

    assert database.connect() is expected_connection
    assert captured["host"] == "db.internal"
    assert captured["port"] == 5432
    assert captured["user"] == "orbit_user"
    assert captured["password"] == "p@ss:word/with-special-characters"
    assert captured["dbname"] == "orbit"
