"""
Performance tests - měření latence API endpoints.

Target: < 100ms pro všechny operace (CLAUDE.md pravidlo #8)
"""
import pytest
import time
from fastapi.testclient import TestClient
from app.gestima_app import app
from app.dependencies import get_current_user
from app.models import User, UserRole


def mock_current_user():
    """Mock authenticated user for performance tests."""
    return User(
        id=1,
        username="test_perf_user",
        email="perf@test.com",
        role=UserRole.ADMIN,
        is_active=True,
        hashed_password="fake_hash",
        created_by="test"
    )


@pytest.fixture
def client():
    """Test client s autentizovaným uživatelem."""
    app.dependency_overrides[get_current_user] = mock_current_user
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_part_detail_latency(client):
    """Změřit latenci načtení detailu dílu."""
    # Warmup
    client.get("/api/parts/1/full")

    # Measure
    start = time.perf_counter()
    response = client.get("/api/parts/1/full")
    latency_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    print(f"\n✓ Part detail latency: {latency_ms:.1f}ms")
    assert latency_ms < 100, f"Too slow! {latency_ms:.1f}ms > 100ms"


def test_operations_list_latency(client):
    """Změřit latenci načtení operací."""
    client.get("/api/operations/part/1")

    start = time.perf_counter()
    response = client.get("/api/operations/part/1")
    latency_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    print(f"\n✓ Operations list latency: {latency_ms:.1f}ms")
    assert latency_ms < 100, f"Too slow! {latency_ms:.1f}ms > 100ms"


def test_batches_list_latency(client):
    """Změřit latenci načtení batchů."""
    client.get("/api/batches/part/1")

    start = time.perf_counter()
    response = client.get("/api/batches/part/1")
    latency_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    print(f"\n✓ Batches list latency: {latency_ms:.1f}ms")
    assert latency_ms < 100, f"Too slow! {latency_ms:.1f}ms > 100ms"


def test_parts_list_latency(client):
    """Změřit latenci načtení seznamu dílů."""
    client.get("/parts")

    start = time.perf_counter()
    response = client.get("/parts")
    latency_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    print(f"\n✓ Parts list latency: {latency_ms:.1f}ms")
    # Parts list může být delší (rendering), ale ne moc
    assert latency_ms < 200, f"Too slow! {latency_ms:.1f}ms > 200ms"


def test_stock_cost_calculation_latency(client):
    """Změřit latenci výpočtu ceny polotovaru."""
    client.get("/api/parts/1/stock-cost")

    start = time.perf_counter()
    response = client.get("/api/parts/1/stock-cost")
    latency_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    print(f"\n✓ Stock cost calculation latency: {latency_ms:.1f}ms")
    assert latency_ms < 100, f"Too slow! {latency_ms:.1f}ms > 100ms"
