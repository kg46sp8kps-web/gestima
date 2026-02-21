"""
Tests for SystemConfig admin console (API + UI).

Tests:
- GET /api/config - list all configs (admin only)
- PUT /api/config/{key} - update config (admin only)
- Optimistic locking
- Non-admin access denied
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.models.config import SystemConfig


class TestSystemConfigAPI:
    """Test SystemConfig REST API endpoints"""

    @pytest.mark.asyncio
    async def test_get_all_configs_admin(self, client: AsyncClient, admin_token):
        """Admin může číst všechny konfigurace"""
        response = await client.get("/api/config/", cookies={"access_token": admin_token})

        assert response.status_code == 200
        configs = response.json()
        assert isinstance(configs, list)
        assert len(configs) == 4  # 4 pricing coefficients

        # Verify expected keys
        keys = {c["key"] for c in configs}
        assert keys == {
            "overhead_coefficient",
            "margin_coefficient",
            "stock_coefficient",
            "coop_coefficient"
        }

        # Verify structure
        for config in configs:
            assert "key" in config
            assert "value_float" in config
            assert "description" in config
            assert "version" in config
            assert config["value_float"] >= 1.0  # All coefficients >= 1.0

    @pytest.mark.asyncio
    async def test_get_all_configs_non_admin(self, client: AsyncClient, operator_token):
        """Non-admin nemůže číst konfigurace"""
        response = await client.get("/api/config/", cookies={"access_token": operator_token})

        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_config_admin(self, client: AsyncClient, admin_token, test_db_session):
        """Admin může upravit koeficient"""
        # Get current config
        result = await test_db_session.execute(
            select(SystemConfig).where(SystemConfig.key == "margin_coefficient")
        )
        config = result.scalar_one()
        old_value = config.value_float
        old_version = config.version

        # Update to new value
        new_value = 1.30
        response = await client.put(
            "/api/config/margin_coefficient",
            cookies={"access_token": admin_token},
            json={
                "value_float": new_value,
                "version": old_version
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "margin_coefficient"
        assert data["value_float"] == new_value
        assert data["version"] == old_version + 1  # Version incremented

        # Verify in database
        await test_db_session.refresh(config)
        assert config.value_float == new_value
        assert config.version == old_version + 1

        # Restore original value for other tests
        await test_db_session.execute(
            select(SystemConfig).where(SystemConfig.key == "margin_coefficient")
        )
        await test_db_session.refresh(config)
        config.value_float = old_value
        await test_db_session.commit()

    @pytest.mark.asyncio
    async def test_update_config_optimistic_locking(self, client: AsyncClient, admin_token, test_db_session):
        """Optimistic locking funguje při konkurentní změně"""
        # Get current config
        result = await test_db_session.execute(
            select(SystemConfig).where(SystemConfig.key == "overhead_coefficient")
        )
        config = result.scalar_one()
        old_version = config.version

        # Try to update with wrong version
        response = await client.put(
            "/api/config/overhead_coefficient",
            cookies={"access_token": admin_token},
            json={
                "value_float": 1.25,
                "version": old_version - 1  # Wrong version
            }
        )

        assert response.status_code == 409
        assert "modified by another user" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_config_non_admin(self, client: AsyncClient, operator_token):
        """Non-admin nemůže upravit koeficient"""
        response = await client.put(
            "/api/config/margin_coefficient",
            cookies={"access_token": operator_token},
            json={
                "value_float": 1.30,
                "version": 1
            }
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_config_nonexistent_key(self, client: AsyncClient, admin_token):
        """Update neexistujícího klíče vrací 404"""
        response = await client.put(
            "/api/config/nonexistent_key",
            cookies={"access_token": admin_token},
            json={
                "value_float": 1.0,
                "version": 1
            }
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_config_description(self, client: AsyncClient, admin_token, test_db_session):
        """Admin může upravit popis koeficientu"""
        # Get current config
        result = await test_db_session.execute(
            select(SystemConfig).where(SystemConfig.key == "stock_coefficient")
        )
        config = result.scalar_one()
        old_description = config.description
        old_version = config.version

        # Update description
        new_description = "Nový popis skladového koeficientu"
        response = await client.put(
            "/api/config/stock_coefficient",
            cookies={"access_token": admin_token},
            json={
                "description": new_description,
                "version": old_version
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == new_description

        # Restore original
        await test_db_session.refresh(config)
        config.description = old_description
        await test_db_session.commit()


class TestSystemConfigUI:
    """Test admin settings page"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Settings page is now in Vue SPA, not a server-side route")
    async def test_settings_page_admin(self, client: AsyncClient, admin_token):
        """Admin může zobrazit settings stránku"""
        response = await client.get("/settings", cookies={"access_token": admin_token}, follow_redirects=False)

        # Should return HTML page (200) or redirect to login if not properly authenticated
        assert response.status_code in [200, 302]

        if response.status_code == 200:
            html = response.text
            assert "Nastavení systému" in html
            assert "overhead_coefficient" in html
            assert "margin_coefficient" in html
            assert "stock_coefficient" in html
            assert "coop_coefficient" in html

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Settings page is now in Vue SPA, not a server-side route")
    async def test_settings_page_non_admin(self, client: AsyncClient, operator_token):
        """Non-admin nemůže zobrazit settings stránku"""
        response = await client.get("/settings", cookies={"access_token": operator_token}, follow_redirects=False)

        # Should return 403 or redirect
        assert response.status_code in [403, 302]
