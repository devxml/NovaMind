from typing import List
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI General Chatbot"

    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    @classmethod
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    LIVEKIT_URL: str = "livekit_url"
    LIVEKIT_API_KEY: str = "********"
    LIVEKIT_API_SECRET: str = "********"

    GOOGLE_API_KEY: str = "********"

    STT_API_URL: str = "http://10.1.2.94:8000/v1/"
    LLM_API_URL: str = "http://10.1.2.94:11434/v1/"
    TTS_API_URL: str = "http://10.1.2.94:3000/api/v1/"
    TTS_API_KEY: str = "********"

    SECRET_KEY: str = "********"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 300

    SQLALCHEMY_DATABASE_URI: str = "sqlite:///./app.db"

    LANGCHAIN_TRACING_V2: bool = 'false'
    LANGSMITH_ENDPOINT: str = "https: // api.smith.langchain.com"
    LANGSMITH_API_KEY: str= "********"
    LANGSMITH_PROJECT: str = "pr-only-surround-27"

    QDRANT_URL: str
    QDRANT_API_KEY: str

    @field_validator("QDRANT_URL")
    @classmethod
    def validate_qdrant_cloud_url(cls, value: str) -> str:
        """Accept only an HTTPS Qdrant Cloud cluster URL."""
        url = value.rstrip("/")
        parsed_url = urlparse(url)
        if (
            parsed_url.scheme != "https"
            or not parsed_url.hostname
            or not parsed_url.hostname.endswith(".cloud.qdrant.io")
        ):
            raise ValueError(
                "QDRANT_URL must be an HTTPS Qdrant Cloud URL, for example "
                "https://<cluster>.cloud.qdrant.io"
            )
        return url

    @field_validator("QDRANT_API_KEY")
    @classmethod
    def validate_qdrant_api_key(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("QDRANT_API_KEY must not be empty")
        return value

    TAVILY_API_KEY: str = "********"
    FIRECRAWL_API_KEY: str = "********"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
