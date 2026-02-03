"""
BillAgent Pro - Test Configuration
===================================
Shared pytest fixtures and configuration.
"""

import asyncio
import os
from datetime import datetime
from decimal import Decimal
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment before importing app
os.environ["ENVIRONMENT"] = "test"
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_DB"] = "test_billagent"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DEBUG"] = "true"

from app.database import Base, get_db
from app.main import app
from app.models import Bill, Vendor, User, LineItem, GLCode
from app.models.bill import BillStatus


# =============================================================================
# Database Fixtures
# =============================================================================
# Use SQLite for tests (faster, no external dependency)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Create async engine for testing."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for testing."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database override."""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()


# =============================================================================
# Model Fixtures
# =============================================================================
@pytest_asyncio.fixture
async def sample_vendor(db_session: AsyncSession) -> Vendor:
    """Create sample vendor for testing."""
    vendor = Vendor(
        name="Test Vendor Corp",
        address="123 Test Street",
        city="Test City",
        state="CA",
        zip_code="90210",
        phone="555-0100",
        email="vendor@test.com",
        tax_id="12-3456789",
        is_active=True,
    )
    db_session.add(vendor)
    await db_session.commit()
    await db_session.refresh(vendor)
    return vendor


@pytest_asyncio.fixture
async def sample_user(db_session: AsyncSession) -> User:
    """Create sample user for testing."""
    from app.services.auth_service import AuthService
    
    user = User(
        email="test@billagent.com",
        username="testuser",
        full_name="Test User",
        hashed_password=AuthService.get_password_hash("testpassword123"),
        is_active=True,
        role="user",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def sample_admin_user(db_session: AsyncSession) -> User:
    """Create sample admin user for testing."""
    from app.services.auth_service import AuthService
    
    user = User(
        email="admin@billagent.com",
        username="admin",
        full_name="Admin User",
        hashed_password=AuthService.get_password_hash("adminpassword123"),
        is_active=True,
        role="admin",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def sample_gl_code(db_session: AsyncSession) -> GLCode:
    """Create sample GL code for testing."""
    gl_code = GLCode(
        code="5000-100",
        description="Office Supplies",
        category="Operating Expenses",
        is_active=True,
    )
    db_session.add(gl_code)
    await db_session.commit()
    await db_session.refresh(gl_code)
    return gl_code


@pytest_asyncio.fixture
async def sample_bill(db_session: AsyncSession, sample_vendor: Vendor) -> Bill:
    """Create sample bill for testing."""
    bill = Bill(
        vendor_id=sample_vendor.id,
        invoice_number="INV-2024-001",
        invoice_date=datetime(2024, 1, 15),
        due_date=datetime(2024, 2, 15),
        subtotal=Decimal("100.00"),
        tax_amount=Decimal("8.25"),
        total_amount=Decimal("108.25"),
        status=BillStatus.PENDING_REVIEW,
        ocr_confidence=0.95,
        payment_terms="Net 30",
        currency="USD",
    )
    db_session.add(bill)
    await db_session.commit()
    await db_session.refresh(bill)
    return bill


@pytest_asyncio.fixture
async def sample_line_item(
    db_session: AsyncSession,
    sample_bill: Bill,
    sample_gl_code: GLCode
) -> LineItem:
    """Create sample line item for testing."""
    line_item = LineItem(
        bill_id=sample_bill.id,
        description="Office Paper",
        quantity=Decimal("10"),
        unit_price=Decimal("10.00"),
        total_price=Decimal("100.00"),
        gl_code_id=sample_gl_code.id,
    )
    db_session.add(line_item)
    await db_session.commit()
    await db_session.refresh(line_item)
    return line_item


# =============================================================================
# Auth Fixtures
# =============================================================================
@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, sample_user: User) -> dict:
    """Get authentication headers for test user."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": sample_user.email,
            "password": "testpassword123",
        },
    )
    assert response.status_code == 200, f"Auth failed: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_auth_headers(client: AsyncClient, sample_admin_user: User) -> dict:
    """Get authentication headers for admin user."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": sample_admin_user.email,
            "password": "adminpassword123",
        },
    )
    assert response.status_code == 200, f"Admin auth failed: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Mock Fixtures
# =============================================================================
@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = MagicMock()
    mock.ping.return_value = True
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    return mock


@pytest.fixture
def mock_celery_app():
    """Mock Celery application."""
    mock = MagicMock()
    mock.send_task.return_value = MagicMock(id="mock-task-id")
    mock.control.inspect.return_value.ping.return_value = {"worker1": {"ok": "pong"}}
    return mock


@pytest.fixture
def mock_ocr_service():
    """Mock OCR service."""
    mock = AsyncMock()
    mock.process_image.return_value = {
        "vendor_name": "Test Vendor",
        "invoice_number": "INV-001",
        "invoice_date": "2024-01-15",
        "total_amount": "108.25",
        "line_items": [
            {"description": "Item 1", "quantity": 1, "unit_price": 100.00, "total": 100.00}
        ],
        "confidence": 0.95,
    }
    return mock
