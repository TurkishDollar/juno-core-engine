from ..modules.contracts import Signal

def fuse(coin: str, signals: list[Signal]) -> Signal:
    usable = [signal for signal in signals if signal.coin.replace('/USDT','') == coin.replace('/USDT','') and signal.decision in {'AL','SAT','BEKLE'}]
    buys = sum(signal.decision == 'AL' for signal in usable)
    sells = sum(signal.decision == 'SAT' for signal in usable)
    decision = 'AL' if buys >= 2 else 'SAT' if sells >= 2 else 'BEKLE'
    reasons = ' | '.join(f'{signal.module}: {signal.decision} — {signal.reason}' for signal in signals)
    return Signal('core', coin, decision, reasons, source='JUNO CORE ENGINE')
