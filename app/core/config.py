from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = "Swim Lab"
    database_url: str = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://swimlab:swimlab-dev@localhost:5432/swimlab",
    )


settings = Settings()
