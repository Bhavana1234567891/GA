from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./ledger.db"
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = ""
    max_agent_steps: int = 2

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_api_key.strip())


settings = Settings()
