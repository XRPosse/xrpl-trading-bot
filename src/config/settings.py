from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from enum import Enum


class NetworkType(str, Enum):
    MAINNET = "mainnet"
    CUSTOM = "custom"


class TradingMode(str, Enum):
    PAPER_TRADING = "paper_trading"
    LIVE = "live"


class Strategy(str, Enum):
    SIMPLE_MOMENTUM = "simple_momentum"
    GRID = "grid"
    ARBITRAGE = "arbitrage"
    MARKET_MAKING = "market_making"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # XRPL Configuration
    xrpl_network: NetworkType = Field(default=NetworkType.MAINNET)
    xrpl_wss_url: str = Field(default="wss://s1.ripple.com:443")
    xrpl_json_rpc_url: str = Field(default="https://s1.ripple.com:51234")
    
    # Wallet Configuration
    wallet_seed: Optional[str] = Field(default=None)
    wallet_address: Optional[str] = Field(default=None)
    
    # Trading Configuration
    trading_pair: str = Field(default="XRP/USDT")
    min_trade_amount: float = Field(default=10.0, gt=0)
    max_trade_amount: float = Field(default=1000.0, gt=0)
    stop_loss_percentage: float = Field(default=5.0, ge=0, le=100)
    take_profit_percentage: float = Field(default=10.0, ge=0, le=100)
    
    # Exchange Configuration
    exchange_name: Optional[str] = Field(default=None)
    exchange_api_key: Optional[str] = Field(default=None)
    exchange_api_secret: Optional[str] = Field(default=None)
    
    # Bot Configuration
    bot_mode: TradingMode = Field(default=TradingMode.PAPER_TRADING)
    strategy: Strategy = Field(default=Strategy.SIMPLE_MOMENTUM)
    update_interval: int = Field(default=60, ge=1)
    
    # Risk Management
    max_open_positions: int = Field(default=3, ge=1)
    max_position_size_pct: float = Field(default=20.0, gt=0, le=100)
    daily_loss_limit: float = Field(default=100.0, ge=0)
    
    # Logging
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="logs/trading_bot.log")
    
    # Database
    database_url: str = Field(default="postgresql://postgres:postgres@localhost:5432/xrpl_trading_bot")
    
    # Monitoring
    enable_metrics: bool = Field(default=True)
    metrics_port: int = Field(default=8000, ge=1024, le=65535)
    
    @field_validator("max_trade_amount")
    def validate_trade_amounts(cls, v, info):
        if "min_trade_amount" in info.data and v <= info.data["min_trade_amount"]:
            raise ValueError("max_trade_amount must be greater than min_trade_amount")
        return v
    
    @field_validator("wallet_seed", "wallet_address")
    def validate_wallet_config(cls, v, info):
        if info.data.get("bot_mode") == TradingMode.LIVE and not v:
            raise ValueError(f"{info.field_name} is required for live trading")
        return v
    
    @property
    def is_testnet(self) -> bool:
        return False  # We only support mainnet now
    
    @property
    def is_live_trading(self) -> bool:
        return self.bot_mode == TradingMode.LIVE
    
    def get_network_urls(self) -> tuple[str, str]:
        if self.xrpl_network == NetworkType.MAINNET:
            return (
                "wss://s1.ripple.com:443",
                "https://s1.ripple.com:51234"
            )
        else:
            return (self.xrpl_wss_url, self.xrpl_json_rpc_url)


def get_settings() -> Settings:
    return Settings()