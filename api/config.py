from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    dna_data_dir: Path = Path("data")
    dna_access_key: str = ""
    dna_allow_local_workspaces: bool = True
    dna_embedded_worker: bool = True
    dna_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    anthropic_api_key: str = ""
    dna_llm_model: str = "anthropic:claude-sonnet-5-5"
    alphagenome_api_key: str = ""
    evo2_forward_url: str = ""
    evo2_base_url: str = ""
    evo2_access_token: str = ""
    dna_reference_grch37: str = ""
    dna_reference_grch38: str = ""
    max_upload_bytes: int = 512 * 1024 * 1024
    max_uncompressed_bytes: int = 2 * 1024 * 1024 * 1024
    max_records: int = 10_000_000

    @property
    def evo2_forward_endpoint(self) -> str:
        if self.evo2_forward_url:
            return self.evo2_forward_url
        return self.evo2_base_url.rstrip("/") + "/biology/arc/evo2/forward" if self.evo2_base_url else ""

    @property
    def cors_origins(self) -> list[str]:
        return [v.strip() for v in self.dna_cors_origins.split(",") if v.strip()]


settings = Settings()
