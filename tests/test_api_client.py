import httpx
import pytest

from vaultgui.api_client import APIClient, AuthError, RateLimitError


def test_login_success():
    def handler(request):
        return httpx.Response(
            200, json={"message": "ok"}, headers={"content-type": "application/json"}
        )

    client = APIClient()
    client.client = httpx.Client(
        base_url="http://localhost", transport=httpx.MockTransport(handler)
    )

    assert client.login("user", "pass") == {"message": "ok"}


def test_login_unauthorized():
    def handler(request):
        return httpx.Response(401)

    client = APIClient()
    client.client = httpx.Client(
        base_url="http://localhost", transport=httpx.MockTransport(handler)
    )

    with pytest.raises(AuthError):
        client.login("user", "wrong")


def test_login_rate_limit():
    def handler(request):
        return httpx.Response(429)

    client = APIClient()
    client.client = httpx.Client(
        base_url="http://localhost", transport=httpx.MockTransport(handler)
    )

    with pytest.raises(RateLimitError):
        client.login("user", "pass")


# ---------- Tahap 9: generator password acak ----------


def test_generate_password_passes_all_params():
    captured = {}

    def handler(request):
        captured["url"] = request.url
        return httpx.Response(
            200,
            json={"password": "password-palsu-123"},
            headers={"content-type": "application/json"},
        )

    client = APIClient()
    client.client = httpx.Client(
        base_url="http://localhost", transport=httpx.MockTransport(handler)
    )

    result = client.generate_password(
        length=20,
        huruf_kecil=True,
        huruf_besar=False,
        angka=True,
        simbol=False,
    )

    assert result == {"password": "password-palsu-123"}
    url = captured["url"]
    assert str(url).startswith("http://localhost/alat/password-acak")
    assert url.params["panjang"] == "20"
    assert url.params["huruf_kecil"] == "true"
    assert url.params["huruf_besar"] == "false"
    assert url.params["angka"] == "true"
    assert url.params["simbol"] == "false"


def test_generate_password_defaults():
    captured = {}

    def handler(request):
        captured["url"] = request.url
        return httpx.Response(
            200,
            json={"password": "password-palsu-123"},
            headers={"content-type": "application/json"},
        )

    client = APIClient()
    client.client = httpx.Client(
        base_url="http://localhost", transport=httpx.MockTransport(handler)
    )

    client.generate_password()

    url = captured["url"]
    assert url.params["panjang"] == "16"
    assert url.params["huruf_kecil"] == "true"
    assert url.params["huruf_besar"] == "true"
    assert url.params["angka"] == "true"
    assert url.params["simbol"] == "false"


def test_generate_password_raises_on_server_error():
    def handler(request):
        return httpx.Response(500)

    client = APIClient()
    client.client = httpx.Client(
        base_url="http://localhost", transport=httpx.MockTransport(handler)
    )

    with pytest.raises(httpx.HTTPStatusError):
        client.generate_password()