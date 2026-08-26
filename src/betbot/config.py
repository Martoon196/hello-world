"""Configuration: secrets from env/.env, tunables from config/settings.yaml."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Secrets(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_api_id: int | None = None
    telegram_api_hash: str | None = None
    telegram_session_name: str = "betbot"

    telegram_bot_token: str | None = None
    telegram_admin_chat_id: str | None = None

    anthropic_api_key: str | None = None

    betfair_username: str | None = None
    betfair_password: str | None = None
    betfair_app_key: str | None = None

    feed_token: str | None = None
    whatsapp_webhook_token: str | None = None
    bfbm_results_token: str | None = None

    betbot_db_path: str = "data/betbot.db"
    betbot_host: str = "0.0.0.0"
    betbot_port: int = 8080


class BankrollCfg(BaseModel):
    opening_cents: int = 100000
    currency: str = "EUR"


class StakingCfg(BaseModel):
    base_pct: float = 0.02
    absolute_max_stake_cents: int = 10000
    min_stake_cents: int = 200
    liquidity_max_pct: float = 0.10


class PriceRuleCfg(BaseModel):
    default_floor_pct: float = 0.20


class LimitsCfg(BaseModel):
    max_bets_per_day: int = 15
    daily_loss_limit_pct: float = 0.10
    max_open_exposure_pct: float = 0.25
    too_close_to_off_seconds: int = 120


class ParsingCfg(BaseModel):
    model: str = "claude-sonnet-5"
    min_confidence: float = 0.80
    max_retries: int = 3


class MatchingCfg(BaseModel):
    min_match_score: float = 88
    race_time_window_minutes: int = 10
    catalogue_cache_ttl_seconds: int = 300
    countries: list[str] = ["GB", "IE"]


class FeedCfg(BaseModel):
    bet_expiry_before_off_seconds: int = 60
    expected_poll_interval_seconds: int = 30


class WatchdogCfg(BaseModel):
    telegram_quiet_alert_hours: int = 3
    whatsapp_heartbeat_stale_minutes: int = 45
    racing_hours_utc: list[int] = [9, 21]


class SettlementCfg(BaseModel):
    results_poll_interval_seconds: int = 120
    estimate_after_hours: int = 4
    commission_pct: float = 0.05


class NotificationsCfg(BaseModel):
    daily_summary_hour_utc: int = 21


class Tunables(BaseModel):
    bankroll: BankrollCfg = BankrollCfg()
    staking: StakingCfg = StakingCfg()
    price_rule: PriceRuleCfg = PriceRuleCfg()
    limits: LimitsCfg = LimitsCfg()
    parsing: ParsingCfg = ParsingCfg()
    matching: MatchingCfg = MatchingCfg()
    feed: FeedCfg = FeedCfg()
    watchdog: WatchdogCfg = WatchdogCfg()
    settlement: SettlementCfg = SettlementCfg()
    notifications: NotificationsCfg = NotificationsCfg()


@lru_cache
def secrets() -> Secrets:
    return Secrets()


@lru_cache
def tunables(path: str | None = None) -> Tunables:
    yaml_path = Path(path) if path else PROJECT_ROOT / "config" / "settings.yaml"
    if yaml_path.exists():
        return Tunables.model_validate(yaml.safe_load(yaml_path.read_text()) or {})
    return Tunables()
