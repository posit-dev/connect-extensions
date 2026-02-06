from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Slack tokens
    slack_bot_token: str  # xoxb-...
    slack_app_token: str  # xapp-... (for Socket Mode)

    class Config:
        env_file = ".env"


settings = Settings()
