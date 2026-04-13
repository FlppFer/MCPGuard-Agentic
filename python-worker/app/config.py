from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Go API callback
    mcpguard_api_url: str = Field(default="http://mcpguard-api:8080", alias="MCPGUARD_API_URL")
    mcpguard_api_key: str = Field(default="dev-key", alias="MCPGUARD_API_KEY")
    mcpguard_client_id: str = Field(default="dev-client", alias="MCPGUARD_CLIENT_ID")

    # S3 / Storage
    aws_access_key_id: str = Field(default="", alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(default="", alias="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    s3_bucket: str = Field(default="mcpguard-local-storage", alias="S3_BUCKET")
    s3_endpoint: str = Field(default="", alias="S3_ENDPOINT")
    storage_mode: str = Field(default="s3", alias="STORAGE_MODE")
    local_storage_path: str = Field(default="/app/mcpguard-local-storage", alias="LOCAL_STORAGE_PATH")

    # LLM (Google Gemini free tier — https://aistudio.google.com/app/apikey)
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_model: str = Field(default="gemini-3.0-flash", alias="LLM_MODEL")

    # Worker
    worker_port: int = Field(default=5000, alias="WORKER_PORT")
    log_level: str = Field(default="info", alias="LOG_LEVEL")

    model_config = {"populate_by_name": True, "env_file": ".env", "extra": "ignore"}


settings = Settings()
