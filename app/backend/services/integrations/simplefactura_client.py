"""Cliente HTTP para integración SimpleFactura."""

import requests


class SimpleFacturaClient:
    BASE_URL = "https://api.simplefactura.cl"

    def fetch_token(self, email: str, password: str) -> dict:
        response = requests.post(
            f"{self.BASE_URL}/token",
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def is_token_valid(self, access_token: str) -> bool:
        response = requests.get(
            f"{self.BASE_URL}/token/expire",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )
        return response.status_code == 200
