"""API test setup: env vars are set BEFORE importing the app so Settings
picks them up. Uses a throwaway SQLite file and test upload/console dirs."""

import os
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
os.environ["DATABASE_URL"] = "sqlite:///./.test-netlab.db"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["LABS_DIR"] = str(REPO_ROOT / "labs")
os.environ["UPLOAD_DIR"] = str(REPO_ROOT / ".test-uploads")
os.environ["CONSOLE_LOG_DIR"] = str(REPO_ROOT / ".test-console-logs")

import pytest  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.models import User  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    student = User(email="student@example.com", name="Test Student", role="student")
    instructor = User(
        email="instructor@example.com", name="Test Instructor", role="instructor"
    )
    db.add(student)
    db.add(instructor)
    db.commit()
    db.refresh(student)
    db.refresh(instructor)
    yield {"student": student, "instructor": instructor}
    db.close()
    Base.metadata.drop_all(bind=engine)
    for path in (".test-netlab.db", ".test-uploads", ".test-console-logs"):
        target = REPO_ROOT / path
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def student_token(_db):
    return create_access_token(subject=str(_db["student"].id), role="student")


@pytest.fixture
def instructor_token(_db):
    return create_access_token(subject=str(_db["instructor"].id), role="instructor")


@pytest.fixture
def student_headers(student_token):
    return {"Authorization": f"Bearer {student_token}"}


@pytest.fixture
def instructor_headers(instructor_token):
    return {"Authorization": f"Bearer {instructor_token}"}
