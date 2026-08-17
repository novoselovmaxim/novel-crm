from urllib.parse import quote_plus
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "novel"
    db_password: str = "novel_secret"
    db_name: str = "novel_crm"
    jwt_secret: str = "change_me_in_production"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 30
    smtp_host: str = "mail.netangels.ru"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    base_url: str = "https://novel.maxnov.ru"
    tavily_api_key: str = ""
    zveno_api_key: str = ""
    zveno_base_url: str = "https://api.zveno.ai/v1"
    llm_model: str = "openai/gpt-4o-mini"

    @property
    def db_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{quote_plus(self.db_password)}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    class Config:
        env_file = ".env"

settings = Settings()

engine = create_async_engine(settings.db_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        yield session
