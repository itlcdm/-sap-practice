from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    sap_url: str
    sap_company_db: str
    sap_username: str
    sap_password: str
    sap_verify_ssl: bool = False

    admin_email: str
    admin_password: str

    db_host: str
    db_port: int = 5432
    db_name: str
    db_user: str
    db_password: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


settings = Settings()