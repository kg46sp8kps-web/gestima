"""GESTIMA - Tests for Accounting Router (CsiXls Proxy)"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_get_balances_no_token(client: AsyncClient, admin_headers: dict):
    """Test balances endpoint returns 501 when API token not configured."""
    with patch("app.routers.accounting_router.settings.CSIXLS_API_TOKEN", ""):
        response = await client.get("/api/accounting/balances?rok=2026", headers=admin_headers)
        assert response.status_code == 501
        assert "not configured" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_turnovers_no_token(client: AsyncClient, admin_headers: dict):
    """Test turnovers endpoint returns 501 when API token not configured."""
    with patch("app.routers.accounting_router.settings.CSIXLS_API_TOKEN", ""):
        response = await client.get("/api/accounting/turnovers?rok=2026", headers=admin_headers)
        assert response.status_code == 501
        assert "not configured" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_balances_with_mock_data(client: AsyncClient, admin_headers: dict):
    """Test balances endpoint with mocked CsiXls API response."""
    mock_data = [
        {
            "rok": 2026,
            "mesic": 1,
            "ucet": "221",
            "popis": "Materiál",
            "pocatecni": 100000.0,
            "konecny": 105000.0,
        },
        {
            "rok": 2026,
            "mesic": 2,
            "ucet": "221",
            "popis": "Materiál",
            "pocatecni": 105000.0,
            "konecny": 110000.0,
        },
    ]

    with patch("app.routers.accounting_router.settings.CSIXLS_API_TOKEN", "test-token"):
        with patch("app.routers.accounting_router._fetch_csixls", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data

            response = await client.get("/api/accounting/balances?rok=2026", headers=admin_headers)

            assert response.status_code == 200
            data = response.json()

            assert data["rok"] == 2026
            assert "221" in data["accounts"]
            assert data["account_names"]["221"] == "Materiál"
            assert data["total_records"] == 2
            assert "1" in data["cells"]["221"]
            assert "2" in data["cells"]["221"]
            assert data["cells"]["221"]["1"]["pocatecni"] == 100000.0
            assert data["cells"]["221"]["1"]["konecny"] == 105000.0


@pytest.mark.asyncio
async def test_get_turnovers_with_mock_data(client: AsyncClient, admin_headers: dict):
    """Test turnovers endpoint with mocked CsiXls API response."""
    mock_data = [
        {
            "rok": 2026,
            "mesic": 1,
            "ucet": "501",
            "popis": "Spotřeba materiálu",
            "md": 50000.0,
            "dal": 0.0,
            "dAn1": "MAT001",
            "dAn2": "DIV01",
            "dAn3": "",
            "dAn4": "",
        },
        {
            "rok": 2026,
            "mesic": 1,
            "ucet": "601",
            "popis": "Tržby z prodeje",
            "md": 0.0,
            "dal": 100000.0,
            "dAn1": "CUS001",
            "dAn2": "DIV01",
            "dAn3": "",
            "dAn4": "",
        },
    ]

    with patch("app.routers.accounting_router.settings.CSIXLS_API_TOKEN", "test-token"):
        with patch("app.routers.accounting_router._fetch_csixls", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data

            response = await client.get("/api/accounting/turnovers?rok=2026", headers=admin_headers)

            assert response.status_code == 200
            data = response.json()

            assert data["rok"] == 2026
            assert data["total_records"] == 2
            assert data["non_zero_records"] == 2
            assert len(data["records"]) == 2

            # Check first record
            assert data["records"][0]["ucet"] == "501"
            assert data["records"][0]["md"] == 50000.0
            assert data["records"][0]["dAn1"] == "MAT001"

            # Check analytics
            assert "dAn1" in data["analytics"]
            assert "MAT001" in data["analytics"]["dAn1"]
            assert "CUS001" in data["analytics"]["dAn1"]


@pytest.mark.asyncio
async def test_cache_functionality(client: AsyncClient, admin_headers: dict):
    """Test that caching works correctly."""
    import app.routers.accounting_router as accounting_router

    # Clear cache before test
    accounting_router._cache.clear()

    mock_data = [
        {
            "rok": 2026,
            "mesic": 1,
            "ucet": "221",
            "popis": "Materiál",
            "pocatecni": 100000.0,
            "konecny": 105000.0,
        },
    ]

    with patch("app.routers.accounting_router.settings.CSIXLS_API_TOKEN", "test-token"):
        with patch("app.routers.accounting_router._fetch_csixls", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data

            # First call - should hit API
            response1 = await client.get("/api/accounting/balances?rok=2026", headers=admin_headers)
            assert response1.status_code == 200
            assert mock_fetch.call_count == 1

            # Second call - should use cache
            response2 = await client.get("/api/accounting/balances?rok=2026", headers=admin_headers)
            assert response2.status_code == 200
            assert mock_fetch.call_count == 1  # Still 1 (cache hit)

            # Responses should be identical
            assert response1.json() == response2.json()


@pytest.mark.asyncio
async def test_refresh_cache(client: AsyncClient, admin_headers: dict):
    """Test cache refresh endpoint."""
    response = await client.post("/api/accounting/refresh?rok=2026", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "2026" in data["message"]


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    """Test that endpoints require authentication."""
    response = await client.get("/api/accounting/balances?rok=2026")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_non_zero_accounts_calculation(client: AsyncClient, admin_headers: dict):
    """Test that non_zero_accounts is calculated correctly."""
    mock_data = [
        {
            "rok": 2026,
            "mesic": 1,
            "ucet": "221",
            "popis": "Materiál",
            "pocatecni": 100000.0,
            "konecny": 105000.0,
        },
        {
            "rok": 2026,
            "mesic": 1,
            "ucet": "222",
            "popis": "Zboží",
            "pocatecni": 0.0,
            "konecny": 0.0,
        },
    ]

    with patch("app.routers.accounting_router.settings.CSIXLS_API_TOKEN", "test-token"):
        with patch("app.routers.accounting_router._fetch_csixls", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data

            response = await client.get("/api/accounting/balances?rok=2026", headers=admin_headers)

            assert response.status_code == 200
            data = response.json()

            # Only 221 is non-zero
            assert data["non_zero_accounts"] == 1


@pytest.mark.asyncio
async def test_dashboard_overview_yoy_comparison(client: AsyncClient, admin_headers: dict):
    """Test dashboard overview endpoint with YoY comparison."""
    current_year_balance = [
        {
            "rok": 2026,
            "mesic": 1,
            "ucet": "221",
            "popis": "Cash",
            "pocatecni": 50000.0,
            "konecny": 60000.0,
        },
        {
            "rok": 2026,
            "mesic": 1,
            "ucet": "121",
            "popis": "Inventory",
            "pocatecni": 30000.0,
            "konecny": 35000.0,
        },
    ]

    current_year_turnover = [
        {
            "rok": 2026,
            "mesic": 1,
            "ucet": "601000",
            "popis": "Revenue",
            "md": 0.0,
            "dal": 120000.0,
            "dAn1": "",
            "dAn2": "",
            "dAn3": "",
            "dAn4": "",
        },
        {
            "rok": 2026,
            "mesic": 1,
            "ucet": "501000",
            "popis": "Expenses",
            "md": 80000.0,
            "dal": 0.0,
            "dAn1": "",
            "dAn2": "",
            "dAn3": "",
            "dAn4": "",
        },
    ]

    previous_year_balance = [
        {
            "rok": 2025,
            "mesic": 1,
            "ucet": "221",
            "popis": "Cash",
            "pocatecni": 45000.0,
            "konecny": 50000.0,
        },
    ]

    previous_year_turnover = [
        {
            "rok": 2025,
            "mesic": 1,
            "ucet": "601000",
            "popis": "Revenue",
            "md": 0.0,
            "dal": 100000.0,
            "dAn1": "",
            "dAn2": "",
            "dAn3": "",
            "dAn4": "",
        },
        {
            "rok": 2025,
            "mesic": 1,
            "ucet": "501000",
            "popis": "Expenses",
            "md": 70000.0,
            "dal": 0.0,
            "dAn1": "",
            "dAn2": "",
            "dAn3": "",
            "dAn4": "",
        },
    ]

    with patch("app.routers.accounting_router.settings.CSIXLS_API_TOKEN", "test-token"):
        with patch("app.routers.accounting_router._fetch_csixls", new_callable=AsyncMock) as mock_fetch:
            # Configure mock to return different data based on endpoint
            def side_effect(endpoint):
                if "2026" in endpoint:
                    if "ZustNaUctech" in endpoint:
                        return current_year_balance
                    elif "ZustNaDan" in endpoint:
                        return current_year_turnover
                elif "2025" in endpoint:
                    if "ZustNaUctech" in endpoint:
                        return previous_year_balance
                    elif "ZustNaDan" in endpoint:
                        return previous_year_turnover
                return []

            mock_fetch.side_effect = side_effect

            response = await client.get("/api/accounting/dashboard/overview?rok=2026", headers=admin_headers)

            assert response.status_code == 200
            data = response.json()

            # Current year metrics
            assert data["rok"] == 2026
            assert data["ytd_revenue"] == 120000.0
            assert data["ytd_expenses"] == 80000.0
            assert data["ytd_profit"] == 40000.0

            # Previous year metrics
            assert data["prev_ytd_revenue"] == 100000.0
            assert data["prev_ytd_expenses"] == 70000.0
            assert data["prev_ytd_profit"] == 30000.0

            # YoY comparison (should be approximately 20% revenue growth)
            assert data["revenue_yoy_pct"] is not None
            assert abs(data["revenue_yoy_pct"] - 20.0) < 0.1

            # Profit YoY (should be approximately 33.33% growth)
            assert data["profit_yoy_pct"] is not None
            assert abs(data["profit_yoy_pct"] - 33.33) < 0.1

            # Margin delta (should be positive)
            assert data["margin_delta_pp"] is not None

            # Efficiency ratios should be present
            assert data["days_cash_on_hand"] is not None
            assert data["receivables_to_revenue_pct"] is not None
            assert data["inventory_to_revenue_pct"] is not None
