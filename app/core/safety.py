from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from ..config import Settings, get_settings
from ..models import Trade

class SafetyError(RuntimeError):
    pass

def assert_testnet_only(settings: Settings) -> None:
    if not settings.binance_testnet:
        raise SafetyError('BINANCE_TESTNET=true olmadan işlem katmanı başlatılamaz.')
    if settings.trading_enabled and not settings.testnet_ready:
        raise SafetyError('Testnet emirleri için Binance Testnet API anahtarı ve secret gereklidir.')

def order_allowed(settings: Settings, daily_loss_pct: float) -> bool:
    assert_testnet_only(settings)
    return settings.order_execution_ready and daily_loss_pct < 2.0

async def daily_loss_pct(session: AsyncSession) -> float:
    result = await session.execute(select(func.coalesce(func.sum(Trade.realized_pnl), 0.0)).where(Trade.status == 'filled', Trade.created_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)))
    realized_pnl = float(result.scalar_one() or 0.0)
    starting_balance = get_settings().starting_testnet_balance_usdt
    return max(0.0, (-realized_pnl / starting_balance) * 100) if starting_balance > 0 else 100.0
