import pytest
from unittest.mock import patch, MagicMock
from fastapi import Request
from starlette.datastructures import Headers

from app.core.exceptions import AuthenticationError, RateLimitExceededError
from app.core.auth import verify_gateway_token


class TestVerifyGatewayToken:
    @pytest.fixture
    def mock_request(self):
        def _make_request(headers_dict):
            request = MagicMock(spec=Request)
            request.headers = Headers(headers_dict)
            return request
        return _make_request

    @pytest.mark.asyncio
    @patch("app.core.auth._token", "my-secret-token")
    @patch("app.core.auth._rate_limiter.check", return_value=True)
    async def test_valid_token(self, mock_check, mock_request):
        """Valid Bearer token → returns token string."""
        request = mock_request({"Authorization": "Bearer my-secret-token"})
        token = await verify_gateway_token(request)
        assert token == "my-secret-token"

    @pytest.mark.asyncio
    @patch("app.core.auth._token", "my-secret-token")
    async def test_invalid_token(self, mock_request):
        """Wrong token → raises AuthenticationError."""
        request = mock_request({"Authorization": "Bearer wrong-token"})
        with pytest.raises(AuthenticationError) as exc_info:
            await verify_gateway_token(request)
        assert "Invalid token" in exc_info.value.message

    @pytest.mark.asyncio
    @patch("app.core.auth._token", "my-secret-token")
    async def test_missing_header(self, mock_request):
        """No Authorization header → raises AuthenticationError."""
        request = mock_request({})
        with pytest.raises(AuthenticationError) as exc_info:
            await verify_gateway_token(request)
        assert "Missing Authorization header" in exc_info.value.message

    @pytest.mark.asyncio
    @patch("app.core.auth._token", "my-secret-token")
    async def test_malformed_header_no_bearer(self, mock_request):
        """'Token xxx' format → raises AuthenticationError."""
        request = mock_request({"Authorization": "Token my-secret-token"})
        with pytest.raises(AuthenticationError) as exc_info:
            await verify_gateway_token(request)
        assert "Invalid format" in exc_info.value.message

    @pytest.mark.asyncio
    @patch("app.core.auth._token", "my-secret-token")
    async def test_malformed_header_empty_token(self, mock_request):
        """'Bearer ' format → raises AuthenticationError."""
        request = mock_request({"Authorization": "Bearer "})
        with pytest.raises(AuthenticationError) as exc_info:
            await verify_gateway_token(request)
        assert "Empty token" in exc_info.value.message

    @pytest.mark.asyncio
    @patch("app.core.auth._token", "")
    async def test_auth_disabled(self, mock_request):
        """_token='' → returns None without checks."""
        request = mock_request({"Authorization": "Bearer valid-but-ignored"})
        token = await verify_gateway_token(request)
        assert token is None

    @pytest.mark.asyncio
    @patch("app.core.auth._token", "my-secret-token")
    @patch("app.core.auth._rate_limiter.check", return_value=False)
    @patch("app.core.auth._rate_limiter._max_rpm", 120)
    async def test_rate_limit_exceeded(self, mock_check, mock_request):
        """Rate limiter returns False → raises RateLimitExceededError."""
        request = mock_request({"Authorization": "Bearer my-secret-token"})
        with pytest.raises(RateLimitExceededError) as exc_info:
            await verify_gateway_token(request)
        assert exc_info.value.code == "RATE_LIMIT_EXCEEDED"


class TestAuthIntegration:
    def test_public_health_endpoint(self):
        """GET /health without token → 200."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_protected_endpoint_without_token(self):
        from fastapi.testclient import TestClient
        from app.main import app

        # Enable auth for this test specifically
        with patch("app.core.auth._token", "test-token"):
            client = TestClient(app)
            response = client.get("/api/v1/models")
            assert response.status_code == 401
            assert response.json()["code"] == "AUTHENTICATION_FAILED"
