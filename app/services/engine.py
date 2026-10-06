import asyncio
import json
import logging
from sqlalchemy import select
from ..config import Settings
from ..db import SessionLocal
from ..models import Decision, Event, Trade
from ..modules.exchange import BinanceTestnet, grid_rsi_signal
from ..modules.sentiment import SentimentAgent
from ..modules.whales import WhaleWatcher
from ..core.fusion import fuse
from .telegram import TelegramService

log = logging.getLogger('juno')

class CoreEngine:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.exchange = BinanceTestnet(settings)
        self.whales = WhaleWatcher(settings)
        self.sentiment = SentimentAgent(settings)
        self.telegram: TelegramService | None = None
        self.running = True
        self.last_signals = []

    async def status_text(self) -> str:
        return f'🤖 JUNO CORE ENGINE\nÇalışıyor: {self.running}\nTestnet: {self.settings.binance_testnet}\nEmir katmanı: {self.settings.order_execution_ready}\nSon sinyal sayısı: {len(self.last_signals)}'

    async def run_market_cycle(self) -> None:
        if not self.settings.testnet_ready:
            return
        snapshot = await self.exchange.snapshot('BTC/USDT')
        trading_signal = grid_rsi_signal(snapshot)
        ai_signal = await self.sentiment.analyze('BTC')
        core_signal = fuse('BTC', [trading_signal, ai_signal])
        self.last_signals = [trading_signal, ai_signal, core_signal]
        async with SessionLocal() as session:
            for signal in self.last_signals:
                session.add(Decision(coin=signal.coin, decision=signal.decision, reason=signal.reason, module_votes=json.dumps({'module':signal.module})))
            await session.commit()
        if self.telegram:
            for signal in self.last_signals:
                if signal.decision not in {'UNAVAILABLE', 'BEKLE'}:
                    await self.telegram.send(f'🤖 JUNO: {signal.module.upper()} - {signal.coin} - {signal.decision} - {signal.reason}')

    async def run_whale_cycle(self) -> None:
        transfers = await self.whales.poll()
        async with SessionLocal() as session:
            for transfer in transfers:
                labelled = await self.whales.label(transfer)
                payload = json.dumps(labelled.__dict__, default=str)
                session.add(Event(event_type='whale_transfer', coin=labelled.asset, payload=payload))
                if self.telegram:
                    await self.telegram.send(f'🤖 JUNO: BALİNA - {labelled.asset} - BEKLE - {labelled.amount:,.2f} transfer; etiket: {labelled.label or "etiket yok"}')
            await session.commit()

    async def market_loop(self):
        while True:
            if not self.running:
                await asyncio.sleep(1)
                continue
            try:
                await self.run_market_cycle()
            except Exception:
                log.exception('market cycle failed')
            await asyncio.sleep(self.settings.market_poll_seconds)

    async def whale_loop(self):
        while True:
            if not self.running:
                await asyncio.sleep(1)
                continue
            try:
                await self.run_whale_cycle()
            except Exception:
                log.exception('whale cycle failed')
            await asyncio.sleep(self.settings.whale_poll_seconds)

    async def stop(self):
        self.running = False
        await self.exchange.close()

    async def resume(self):
        self.running = True
