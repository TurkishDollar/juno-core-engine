import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import ccxt.async_support as ccxt
from ..config import Settings
from ..core.safety import SafetyError, assert_testnet_only, order_allowed

@dataclass
class MarketSnapshot:
    symbol: str
    price: float
    rsi: float | None
    source: str
    observed_at: datetime

class BinanceTestnet:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.exchange: ccxt.binance | None = None

    def _client(self) -> ccxt.binance:
        if self.exchange is None:
            if not self.settings.testnet_ready:
                raise SafetyError('Binance Testnet anahtarları henüz tanımlı değil.')
            self.exchange = ccxt.binance({
                'apiKey': self.settings.binance_api_key,
                'secret': self.settings.binance_api_secret,
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'},
            })
            self.exchange.set_sandbox_mode(True)
        return self.exchange

    async def snapshot(self, symbol: str = 'BTC/USDT') -> MarketSnapshot:
        client = self._client()
        ticker = await client.fetch_ticker(symbol)
        ohlcv = await client.fetch_ohlcv(symbol, timeframe='5m', limit=100)
        closes = [float(row[4]) for row in ohlcv]
        rsi = calculate_rsi(closes)
        return MarketSnapshot(symbol, float(ticker['last']), rsi, 'Binance Testnet', datetime.now(timezone.utc))

    async def balance(self) -> dict:
        return await self._client().fetch_balance()

    async def create_order(self, symbol: str, side: str, amount: float, reason: str, daily_loss_pct: float) -> dict:
        if not order_allowed(self.settings, daily_loss_pct):
            raise SafetyError('Emir reddedildi: testnet kapalı veya günlük %2 zarar limiti aşıldı.')
        client = self._client()
        ticker = await client.fetch_ticker(symbol)
        balance = await client.fetch_balance()
        free_quote = float(balance.get('USDT', {}).get('free', 0.0) or 0.0)
        max_quote = free_quote * 0.05
        last_price = float(ticker['last'])
        if amount * last_price > max_quote:
            raise SafetyError('Emir reddedildi: işlem büyüklüğü kasanın %5 sınırını aşıyor.')
        return await client.create_order(symbol, 'market', side, amount, None, {'clientOrderId': 'juno-core'})

    async def close(self) -> None:
        if self.exchange:
            await self.exchange.close()
            self.exchange = None

def calculate_rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) <= period:
        return None
    gains, losses = [], []
    for previous, current in zip(closes[-period-1:-1], closes[-period:]):
        delta = current - previous
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    average_gain = sum(gains) / period
    average_loss = sum(losses) / period
    if average_loss == 0:
        return 100.0
    return 100 - (100 / (1 + average_gain / average_loss))

def grid_rsi_signal(snapshot: MarketSnapshot):
    from .contracts import Signal
    if snapshot.rsi is None:
        return Signal('trading', snapshot.symbol, 'UNAVAILABLE', 'RSI için yeterli gerçek Testnet mum verisi yok.', source=snapshot.source)
    if snapshot.rsi < 30:
        return Signal('trading', snapshot.symbol, 'AL', f'RSI {snapshot.rsi:.2f}; grid alt bandı ve RSI<30.', source=snapshot.source)
    if snapshot.rsi > 70:
        return Signal('trading', snapshot.symbol, 'SAT', f'RSI {snapshot.rsi:.2f}; grid üst bandı ve RSI>70.', source=snapshot.source)
    return Signal('trading', snapshot.symbol, 'BEKLE', f'RSI {snapshot.rsi:.2f}; 30-70 nötr bölge.', source=snapshot.source)
