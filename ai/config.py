from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):

    # --- OpenAI ---
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = "gpt-4o"

    # Embeddings (legal-bert)
    legal_embedding_model: str = "Stern5497/sbert-legal-xlm-roberta-base"
    embedding_dim: int = 768

    # --- Qdrant (Cloud) ---
    qdrant_url: str                     
    qdrant_api_key: str | None = None
    qdrant_collection: str = "corpus"


    # --- S3 ---
    aws_access_key_id: str | None = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str | None = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")
    aws_region: str | None = Field(default=None, alias="AWS_REGION")

    s3_bucket_name: str = Field(alias="S3_BUCKET_NAME")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")
    s3_presign_expires_seconds: int = Field(default=300, alias="S3_PRESIGN_EXPIRES_SECONDS")

    # --- Vector Store ---
    # embedding_model_name: str = "all-MiniLM-L6-v2"
    # qdrant_persist_dir: str = "./qdrant_data"
    # qdrant_collection_name: str = "legal_knowledge"

    # --- FastAPI ---
    app_host: str = "0.0.0.0"
    app_port: int = 8001

    # --- MongoDB ---
    mongodb_uri: str = Field(alias="MONGODB_URI")
    mongodb_db_name: str = Field(alias="MONGODB_DB_NAME")
    ai_service_url: str = Field(default="http://ai:8001", alias="AI_SERVICE_URL")

    langsmith_tracing: bool | None = Field(default=None, alias="LANGSMITH_TRACING")
    langsmith_endpoint: str | None = Field(default=None, alias="LANGSMITH_ENDPOINT")
    langsmith_api_key: str | None = Field(default=None, alias="LANGSMITH_API_KEY")
    langsmith_project: str | None = Field(default=None, alias="LANGSMITH_PROJECT")

    class Config:
        env_file = str(Path(__file__).with_name(".env"))
        env_file_encoding = "utf-8"


settings = Settings()

