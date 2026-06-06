from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "development"
    app_port: int = 8000
    app_host: str = "0.0.0.0"
    cors_origins: list[str] = ["http://localhost:5173"]

    database_url: str

    twilio_account_sid: str
    twilio_auth_token: str
    twilio_whatsapp_number: str  # e.g. whatsapp:+14155238886

    sarvam_api_key: str
    sarvam_api_base: str = "https://api.sarvam.ai"

    paytm_merchant_id: str
    paytm_merchant_key: str
    paytm_environment: str = "staging"  # staging | production

    app_secret_key: str = "changeme"
    debug: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
