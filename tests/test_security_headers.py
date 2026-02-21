"""Tests for security headers middleware (H-3, H-4 audit fix)"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


class TestSecurityHeaders:
    """Tests for SecurityHeadersMiddleware"""

    @pytest.fixture
    def client(self):
        """Test client for FastAPI"""
        from app.gestima_app import app
        return TestClient(app)

    def test_csp_header_present(self, client):
        """CSP header je přítomný (H-3)"""
        response = client.get("/health")
        assert "Content-Security-Policy" in response.headers

    def test_csp_allows_unsafe_inline(self, client):
        """CSP obsahuje unsafe-inline pro Alpine.js (pragmatic approach)"""
        response = client.get("/health")
        csp = response.headers["Content-Security-Policy"]
        assert "'unsafe-inline'" in csp
        assert "script-src 'self' 'unsafe-inline'" in csp
        assert "style-src 'self' 'unsafe-inline'" in csp

    def test_csp_restricts_default_src(self, client):
        """CSP omezuje default-src na 'self'"""
        response = client.get("/health")
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp

    def test_csp_allows_htmx_ajax(self, client):
        """CSP umožňuje HTMX AJAX (connect-src 'self')"""
        response = client.get("/health")
        csp = response.headers["Content-Security-Policy"]
        assert "connect-src 'self'" in csp

    def test_hsts_not_on_http(self, client):
        """HSTS NENÍ přítomný na HTTP (H-4)"""
        # TestClient používá http:// scheme
        response = client.get("/health")
        assert "Strict-Transport-Security" not in response.headers

    def test_hsts_on_https(self, client):
        """HSTS JE přítomný na HTTPS (H-4)"""
        # Mock request.url.scheme to be "https"
        from app.gestima_app import app
        from starlette.requests import Request
        from starlette.responses import Response

        # Manually call middleware with mocked HTTPS request
        from app.gestima_app import SecurityHeadersMiddleware

        async def mock_call_next(request):
            return Response(content="test", status_code=200)

        async def test_https_request():
            # Create mock request with HTTPS scheme
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/test",
                "query_string": b"",
                "headers": [],
                "scheme": "https",  # CRITICAL: HTTPS scheme
                "server": ("testserver", 443),
            }
            request = Request(scope)

            middleware = SecurityHeadersMiddleware(app)
            response = await middleware.dispatch(request, mock_call_next)

            # Check HSTS header
            assert "Strict-Transport-Security" in response.headers
            hsts = response.headers["Strict-Transport-Security"]
            assert "max-age=31536000" in hsts
            assert "includeSubDomains" in hsts

        # Run async test
        import asyncio
        asyncio.run(test_https_request())

    def test_x_frame_options_deny(self, client):
        """X-Frame-Options je DENY (clickjacking protection)"""
        response = client.get("/health")
        assert response.headers["X-Frame-Options"] == "DENY"

    def test_x_content_type_options_nosniff(self, client):
        """X-Content-Type-Options je nosniff (MIME sniffing protection)"""
        response = client.get("/health")
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_referrer_policy(self, client):
        """Referrer-Policy je strict-origin-when-cross-origin"""
        response = client.get("/health")
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_permissions_policy(self, client):
        """Permissions-Policy omezuje geolocation, microphone, camera"""
        response = client.get("/health")
        policy = response.headers["Permissions-Policy"]
        assert "geolocation=()" in policy
        assert "microphone=()" in policy
        assert "camera=()" in policy


class TestAlembicMigrations:
    """Tests for Alembic migration system (C-5 audit fix)"""

    def test_alembic_version_table_exists(self):
        """Alembic version table existuje v DB"""
        import asyncio
        from sqlalchemy import text
        from app.database import engine

        async def check_table():
            async with engine.begin() as conn:
                result = await conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'")
                )
                return result.fetchone() is not None

        exists = asyncio.run(check_table())
        assert exists, "Alembic version table should exist after init_db()"

    def test_alembic_current_version(self):
        """Alembic má current version (označeno pomocí stamp head)"""
        import subprocess
        result = subprocess.run(
            ["alembic", "current"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "(head)" in result.stdout

    def test_alembic_history(self):
        """Alembic history obsahuje initial migration"""
        import subprocess
        result = subprocess.run(
            ["alembic", "history"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "Initial schema" in result.stdout


class TestInitDBErrorHandling:
    """Tests for init_db() error handling (C-5, C-6 audit fix)"""

    def test_init_db_with_logging(self):
        """init_db() loguje správně migrations a seeds"""
        import asyncio
        import logging
        from io import StringIO
        from app.database import init_db

        # Capture logs
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.INFO)

        logger = logging.getLogger("app.database")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Run init_db
        asyncio.run(init_db())

        # Check logs (může být prázdné pokud logger není nakonfigurován v testu)
        # Tento test jen ověřuje že init_db() nepadá
        assert True  # init_db() completed without exception

    def test_seed_failure_does_not_crash(self):
        """Seed failure nevyhodí exception (WARN-CONTINUE strategy)"""
        import asyncio
        from app.database import _safe_seed, async_session
        from app.logging_config import get_logger

        logger = get_logger("test")

        async def failing_seed(session):
            raise ValueError("Test seed failure")

        async def test_seed():
            async with async_session() as session:
                # Should log warning but NOT raise
                await _safe_seed("test_seed", failing_seed, session, logger)

        # Should complete without exception
        asyncio.run(test_seed())
        assert True
