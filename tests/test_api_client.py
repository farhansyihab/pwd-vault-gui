import pytest
import httpx
from vaultgui.api_client import APIClient, AuthError, RateLimitError

def test_login_success():
    def handler(request):
        return httpx.Response(200, json={"message": "ok"}, headers={"content-type": "application/json"})
    
    client = APIClient()
    client.client = httpx.Client(base_url="http://localhost", transport=httpx.MockTransport(handler))
    
    assert client.login("user", "pass") == {"message": "ok"}

def test_login_unauthorized():
    def handler(request):
        return httpx.Response(401)
    
    client = APIClient()
    client.client = httpx.Client(base_url="http://localhost", transport=httpx.MockTransport(handler))
    
    with pytest.raises(AuthError):
        client.login("user", "wrong")

def test_login_rate_limit():
    def handler(request):
        return httpx.Response(429)
    
    client = APIClient()
    client.client = httpx.Client(base_url="http://localhost", transport=httpx.MockTransport(handler))
    
    with pytest.raises(RateLimitError):
        client.login("user", "pass")
