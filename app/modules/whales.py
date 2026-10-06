import json
from dataclasses import dataclass
from datetime import datetime, timezone
import httpx
from ..config import Settings
from .contracts import Signal

# Official Ethereum mainnet contract addresses; values are never generated locally.
TOKENS = {
    'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
    'USDC': '0xA0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',
}

@dataclass
class WhaleTransfer:
    asset: str
    tx_hash: str
    from_address: str
    to_address: str
    amount: float
    observed_at: datetime
    label: str | None = None

class WhaleWatcher:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.last_block: int | None = None

    async def provider_state(self) -> str:
        return 'ONLINE' if self.settings.alchemy_eth_rpc_url else 'UNAVAILABLE'

    async def poll(self) -> list[WhaleTransfer]:
        if not self.settings.alchemy_eth_rpc_url:
            return []
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(self.settings.alchemy_eth_rpc_url, json={'jsonrpc':'2.0','id':1,'method':'eth_blockNumber','params':[]})
            response.raise_for_status()
            latest = int(response.json()['result'], 16)
        if self.last_block is None:
            self.last_block = latest
            return []
        start = self.last_block + 1
        self.last_block = latest
        if start > latest:
            return []
        # Transfer log decoding is deliberately explicit; no fake fallback is used.
        return await self._fetch_transfer_logs(start, latest)

    async def _fetch_transfer_logs(self, start: int, end: int) -> list[WhaleTransfer]:
        transfers: list[WhaleTransfer] = []
        async with httpx.AsyncClient(timeout=20) as client:
            for asset, address in TOKENS.items():
                payload = {'jsonrpc':'2.0','id':1,'method':'eth_getLogs','params':[{'fromBlock':hex(start),'toBlock':hex(end),'address':address,'topics':['0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef']}]}
                response = await client.post(self.settings.alchemy_eth_rpc_url, json=payload)
                response.raise_for_status()
                for item in response.json().get('result', []):
                    amount = int(item['data'], 16) / (10 ** (6 if asset in {'USDT','USDC'} else 18))
                    if amount < self.settings.whale_threshold_usd:
                        continue
                    transfers.append(WhaleTransfer(asset, item['transactionHash'], '0x'+item['topics'][1][-40:], '0x'+item['topics'][2][-40:], amount, datetime.now(timezone.utc)))
        return transfers

    async def label(self, transfer: WhaleTransfer) -> WhaleTransfer:
        if not self.settings.arkham_api_key:
            return transfer
        # Arkham endpoint is provider-specific and requires the user's approved API plan.
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get('https://api.arkhamintelligence.com/intelligence/address/'+transfer.to_address, headers={'API-Key': self.settings.arkham_api_key})
            if response.is_success:
                data = response.json()
                transfer.label = data.get('arkhamEntity', {}).get('name') or data.get('label')
        return transfer

    def as_signal(self, transfer: WhaleTransfer) -> Signal:
        label = transfer.label or transfer.to_address
        return Signal('whale', transfer.asset, 'BEKLE', f'{transfer.amount:,.2f} {transfer.asset} transferi; hedef {label}. Balina olayı alarm olarak iletildi.', source='Alchemy + Arkham')
