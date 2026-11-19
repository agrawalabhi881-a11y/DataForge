from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    app_name: str = "DataForge Backend"
    frontend_url: str = "http://localhost:5173"

    pg_user: str
    pg_password: str
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_database: str

    # Login / sessions
    session_secret_key: str
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:5000/api/v1/auth/google/callback"
    # Where the browser goes after a successful login
    # (the Swagger page for now; change to the frontend URL later)
    post_login_redirect: str = "http://localhost:5000/docs"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def database_url(self) -> URL:
        # URL.create safely handles special characters like # in the password
        return URL.create(
            "postgresql+psycopg2",
            username=self.pg_user,
            password=self.pg_password,
            host=self.pg_host,
            port=self.pg_port,
            database=self.pg_database,
        )


settings = Settings()