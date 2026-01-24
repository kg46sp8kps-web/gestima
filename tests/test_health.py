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

    def test_health_endpoint_returns_200(self, client):
        """Health endpoint vrací 200 když je vše OK"""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self, client):
        """Health response má správnou strukturu"""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert "database" in data

    def test_health_returns_version(self, client):
        """Health vrací správnou verzi"""
        from app.config import settings

        response = client.get("/health")
        data = response.json()

        assert data["version"] == settings.VERSION

    def test_health_reports_healthy_status(self, client):
        """Health reportuje healthy stav"""
        response = client.get("/health")
        data = response.json()

        assert data["status"] == "healthy"
        assert data["database"] == "healthy"

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
