import httpx

from app.config import settings


class SAPService:

    def __init__(self):
        self.base_url = settings.sap_url

        self.client = httpx.AsyncClient(
            verify=settings.sap_verify_ssl,
            timeout=30.0
        )

        self.logged_in = False

    async def login(self):

        payload = {
            "CompanyDB": settings.sap_company_db,
            "UserName": settings.sap_username,
            "Password": settings.sap_password
        }

        response = await self.client.post(
            f"{self.base_url}/Login",
            json=payload
        )

        response.raise_for_status()

        self.logged_in = True

        return response.json()

    async def ensure_login(self):

        if not self.logged_in:
            await self.login()

    async def get(self, endpoint: str):

        await self.ensure_login()

        response = await self.client.get(
            f"{self.base_url}/{endpoint}"
        )

        if response.status_code == 401:
            self.logged_in = False

            await self.login()

            response = await self.client.get(
                f"{self.base_url}/{endpoint}"
            )

        response.raise_for_status()

        return response.json()


sap_service = SAPService()