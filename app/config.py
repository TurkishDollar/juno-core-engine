from functools import lru_cache
from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    app_env: str = 'development'
    database_url: str = 'postgresql+asyncpg://juno:juno@db:5432/juno'
    dashboard_username: str = 'admin'
    dashboard_password: str = Field(min_length=8)
    trading_enabled: bool = False
    binance_testnet: bool = True
    binance_api_key: str = ''
    binance_api_secret: str = ''
    telegram_bot_token: str = ''
    telegram_chat_id: str = ''
    alchemy_eth_rpc_url: str = ''
    arkham_api_key: str = ''
    whale_threshold_usd: float = 500_000
    starting_testnet_balance_usdt: float = 100.0
    lunarcrush_api_key: str = ''
    x_api_bearer_token: str = ''
    openai_api_key: str = ''
    openai_model: str = 'gpt-4o-mini'
    market_poll_seconds: int = 30
    whale_poll_seconds: int = 12
    sentiment_poll_seconds: int = 300

    @field_validator('database_url', mode='before')
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith('postgres://'):
            return 'postgresql+asyncpg://' + value[len('postgres://'):]
        if value.startswith('postgresql://'):
            return 'postgresql+asyncpg://' + value[len('postgresql://'):]
        return value

    @property
    def testnet_ready(self) -> bool:
        return self.binance_testnet and bool(self.binance_api_key and self.binance_api_secret)

    @property
    def order_execution_ready(self) -> bool:
        return self.trading_enabled and self.testnet_ready

@lru_cache
def get_settings() -> Settings:
    return Settings()
