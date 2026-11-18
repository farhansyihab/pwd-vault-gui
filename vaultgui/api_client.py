import httpx
from vaultgui import config


class APIError(Exception):
    pass


class AuthError(APIError):
    pass


class RateLimitError(APIError):
    pass


class APIClient:
    def __init__(self):
        self.base_url = f"http://{config.HOST}:{config.PORT}"
        self.client = httpx.Client(base_url=self.base_url)

    def login(self, username, password):
        resp = self.client.post(
            "/auth/login", data={"username": username, "password": password}
        )
        if resp.status_code == 401:
            raise AuthError("Login gagal")
        if resp.status_code == 429:
            raise RateLimitError("Terlalu banyak percobaan")
        resp.raise_for_status()
        return resp.json()

    def logout(self):
        self.client.post("/auth/logout")

    def get_entries(self, q=""):
        resp = self.client.get("/entri", params={"q": q} if q else None)
        resp.raise_for_status()
        return resp.json()

    def get_entry(self, entry_id):
        resp = self.client.get(f"/entri/{entry_id}")
        resp.raise_for_status()
        return resp.json()

    def create_entry(self, data):
        resp = self.client.post("/entri", json=data)
        resp.raise_for_status()
        return resp.json()

    def update_entry(self, entry_id, data):
        resp = self.client.put(f"/entri/{entry_id}", json=data)
        resp.raise_for_status()
        return resp.json()

    def delete_entry(self, entry_id):
        resp = self.client.delete(f"/entri/{entry_id}")
        resp.raise_for_status()
        return resp.json() if resp.content else None

    def get_entry_password(self, entry_id):
        resp = self.client.get(f"/entri/{entry_id}/password")
        resp.raise_for_status()
        return resp.json()

    def generate_password(
        self,
        length=16,
        huruf_kecil=True,
        huruf_besar=True,
        angka=True,
        simbol=False,
    ):
        """Request a random password from the backend generator.

        Params map straight to the API contract:
        panjang (8-128), huruf_kecil, huruf_besar, angka, simbol.
        Booleans are serialized as lowercase strings to match common
        FastAPI/Pydantic conventions.
        """
        params = {
            "panjang": length,
            "huruf_kecil": str(bool(huruf_kecil)).lower(),
            "huruf_besar": str(bool(huruf_besar)).lower(),
            "angka": str(bool(angka)).lower(),
            "simbol": str(bool(simbol)).lower(),
        }
        resp = self.client.get("/alat/password-acak", params=params)
        resp.raise_for_status()
        return resp.json()