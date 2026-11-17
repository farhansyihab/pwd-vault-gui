import httpx
from vaultgui import config

class APIError(Exception): pass
class AuthError(APIError): pass
class RateLimitError(APIError): pass

class APIClient:
    def __init__(self):
        self.base_url = "http://localhost"
        self.client = httpx.Client(base_url=self.base_url)

    def login(self, username, password):
        resp = self.client.post("/auth/login", data={"username": username, "password": password})
        if resp.status_code == 401: raise AuthError("Login gagal")
        if resp.status_code == 429: raise RateLimitError("Terlalu banyak percobaan")
        resp.raise_for_status()
        return resp.json()

    def logout(self):
        self.client.post("/auth/logout")

    def get_entries(self, q=""):
        resp = self.client.get("/entri", params={"q": q} if q else None)
        resp.raise_for_status()
        return resp.json()

    def get_entry_password(self, entry_id):
        resp = self.client.get(f"/entri/{entry_id}/password")
        resp.raise_for_status()
        return resp.json()

    def generate_password(self, length=16):
        resp = self.client.get("/alat/password-acak", params={"panjang": length})
        resp.raise_for_status()
        return resp.json()
