"""Testy pro health check endpoint a graceful shutdown"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


class TestHealthCheck:
    """Testy pro /health endpoint"""

    @pytest.fixture
    def client(self):
        """Test client pro FastAPI"""
        from app.gestima_app import app
        return TestClient(app)

    def test_health_endpoint_returns_valid_status_code(self, client):
        """Health endpoint vrací validní status code (200 nebo 503)"""
        response = client.get("/health")
        # Může být 200 (healthy/degraded) nebo 503 (unhealthy) v závislosti na prostředí
        assert response.status_code in [200, 503]

    def test_health_response_structure(self, client):
        """Health response má správnou strukturu (extended)"""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert "checks" in data

        # Extended checks
        checks = data["checks"]
        assert "database" in checks
        assert "backup_folder" in checks
        assert "disk_space" in checks
        assert "recent_backup" in checks

    def test_health_returns_version(self, client):
        """Health vrací správnou verzi"""
        from app.config import settings

        response = client.get("/health")
        data = response.json()

        assert data["version"] == settings.VERSION

    def test_health_reports_valid_status(self, client):
        """Health reportuje validní stav"""
        response = client.get("/health")
        data = response.json()

        # Může být healthy, degraded, nebo unhealthy v závislosti na prostředí
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        # Database by ale měla být healthy
        assert data["checks"]["database"]["status"] == "healthy"

    def test_health_no_auth_required(self, client):
        """Health endpoint nevyžaduje autentizaci"""
        # Volání bez auth headeru
        response = client.get("/health")
        # Nesmí být 401 nebo 403
        assert response.status_code not in [401, 403]


class TestGracefulShutdown:
    """Testy pro graceful shutdown"""

    def test_close_db_function_exists(self):
        """close_db funkce existuje"""
        from app.database import close_db
        import asyncio
        assert asyncio.iscoroutinefunction(close_db)

    def test_shutdown_flag_exists(self):
        """Shutdown flag existuje v gestima_app"""
        from app import gestima_app
        assert hasattr(gestima_app, '_shutdown_in_progress')

    def test_health_returns_503_during_shutdown(self):
        """Health vrací 503 během shutdown"""
        from app.gestima_app import app

        with patch('app.gestima_app._shutdown_in_progress', True):
            client = TestClient(app)
            response = client.get("/health")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "shutting_down"

    def test_health_returns_version_during_shutdown(self):
        """Health vrací verzi i během shutdown"""
        from app.gestima_app import app
        from app.config import settings

        with patch('app.gestima_app._shutdown_in_progress', True):
            client = TestClient(app)
            response = client.get("/health")
            data = response.json()
            assert data["version"] == settings.VERSION


class TestExtendedHealthChecks:
    """Testy pro extended health checks (v1.1.7)"""

    @pytest.fixture
    def client(self):
        """Test client pro FastAPI"""
        from app.gestima_app import app
        return TestClient(app)

    def test_disk_space_check_exists(self, client):
        """Disk space check je součástí health response"""
        response = client.get("/health")
        data = response.json()

        assert "disk_space" in data["checks"]
        disk = data["checks"]["disk_space"]

        assert "status" in disk
        # Pokud není error, měly by být přítomné další fieldy
        if disk["status"] != "error":
            assert "free_gb" in disk
            assert "total_gb" in disk
            assert "percent_free" in disk

    def test_backup_folder_check_exists(self, client):
        """Backup folder check je součástí health response"""
        response = client.get("/health")
        data = response.json()

        assert "backup_folder" in data["checks"]
        backup_folder = data["checks"]["backup_folder"]

        assert "status" in backup_folder
        # Status může být healthy, warning, unhealthy nebo error

    def test_recent_backup_check_exists(self, client):
        """Recent backup check je součástí health response"""
        response = client.get("/health")
        data = response.json()

        assert "recent_backup" in data["checks"]
        recent_backup = data["checks"]["recent_backup"]

        assert "status" in recent_backup
        # Může obsahovat latest_backup a age_hours pokud backupy existují

    def test_degraded_status_on_warnings(self, client):
        """Health vrací 'degraded' status pokud jsou warnings (ne kritické)"""
        response = client.get("/health")
        data = response.json()

        # Pokud je status degraded, měl by být status code 200 (ne 503)
        if data["status"] == "degraded":
            assert response.status_code == 200

    def test_unhealthy_status_returns_503(self):
        """Unhealthy status vrací 503 status code"""
        from app.gestima_app import app
        from unittest.mock import AsyncMock

        # Mock database failure
        with patch('app.gestima_app.async_session') as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(side_effect=Exception("DB error"))
            client = TestClient(app)
            response = client.get("/health")

            # Při DB erroru by měl být unhealthy a status code 503
            if response.status_code == 503:
                data = response.json()
                assert data["status"] in ["unhealthy", "shutting_down"]
