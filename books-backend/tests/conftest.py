import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import create_user
from app.database import get_db
from app.models import Base
from main import app

# Use in-memory SQLite database for tests
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override the get_db dependency for tests."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_credentials():
    """Standard test user credentials."""
    return {"username": "testuser", "password": "testpass123"}


@pytest.fixture
def test_user(db_session, test_user_credentials):
    """Create a test user directly in the database and return credentials."""
    create_user(db_session, test_user_credentials["username"], test_user_credentials["password"])
    return test_user_credentials


@pytest.fixture
def auth_headers(test_user):
    """Get HTTP Basic Auth headers for test user."""
    from base64 import b64encode
    credentials = f"{test_user['username']}:{test_user['password']}"
    encoded = b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


@pytest.fixture
def sample_book_data():
    """Sample book data for testing."""
    return {
        "title": "Test Book",
        "author": "Test Author",
        "isbn": "1234567890",
        "description": "A test book",
        "page_count": 300
    }
