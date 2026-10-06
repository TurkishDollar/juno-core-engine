from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

Decision = Literal['AL', 'SAT', 'BEKLE', 'UNAVAILABLE']

@dataclass
class Signal:
    module: str
    coin: str
    decision: Decision
    reason: str
    confidence: float | None = None
    source: str = ''
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class ProviderState:
    provider: str
    status: Literal['ONLINE', 'OFFLINE', 'ERROR', 'UNAVAILABLE']
    detail: str = ''
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
