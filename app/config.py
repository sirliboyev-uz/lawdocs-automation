from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Law Firm Document Automation"
    storage_dir: Path = Path("storage")
    database_url: str = "sqlite:///./data.db"

    # LLM — set provider to "anthropic" or "gemini"
    llm_provider: str = "gemini"
    llm_model: str = "gemini-2.0-flash"

    # Provider keys (only the one matching llm_provider is required)
    anthropic_api_key: str = ""
    google_api_key: str = ""
    openai_api_key: str = ""

    # Upload constraints
    max_upload_size_mb: int = 50
    supported_extensions: list[str] = [
        ".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif",
    ]

    # Classification categories
    document_categories: list[str] = [
        "Deposition Transcript",
        "Contract",
        "Court Filing",
        "Correspondence",
        "Invoice",
        "Medical Record",
        "Police Report",
        "Expert Report",
        "Other",
    ]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
