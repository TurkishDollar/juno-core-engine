import asyncio
import json
import secrets
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Request, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from .config import get_settings
from .db import init_db, SessionLocal
from .models import Decision, Event, Trade
from .services.engine import CoreEngine
from .services.telegram import TelegramService

settings = get_settings()
engine = CoreEngine(settings)
templates = Jinja2Templates(directory='templates')
basic_auth = HTTPBasic()

def require_dashboard_auth(credentials: HTTPBasicCredentials = Depends(basic_auth)) -> str:
    valid_user = secrets.compare_digest(credentials.username, settings.dashboard_username)
    valid_password = secrets.compare_digest(credentials.password, settings.dashboard_password)
    if not (valid_user and valid_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Dashboard kimlik doğrulaması gerekli.', headers={'WWW-Authenticate': 'Basic'})
    return credentials.username

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    telegram_service = TelegramService(settings, engine.status_text, engine.stop, engine.resume)
    engine.telegram = telegram_service
    telegram_app = telegram_service.build()
    if telegram_app:
        await telegram_app.initialize()
        await telegram_app.start()
        if telegram_app.updater:
            await telegram_app.updater.start_polling()
    tasks = [asyncio.create_task(engine.market_loop()), asyncio.create_task(engine.whale_loop())]
    yield
    await engine.stop()
    if telegram_app:
        if telegram_app.updater:
            await telegram_app.updater.stop()
        await telegram_app.stop()
        await telegram_app.shutdown()
    for task in tasks:
        task.cancel()

app = FastAPI(title='JUNO CORE ENGINE', lifespan=lifespan)

@app.get('/health')
async def health():
    return {'ok': True, 'running': engine.running, 'testnet': settings.binance_testnet, 'order_execution_ready': settings.order_execution_ready}

@app.get('/api/status')
async def status(_: str = Depends(require_dashboard_auth)):
    async with SessionLocal() as session:
        decisions = (await session.execute(select(Decision).order_by(Decision.created_at.desc()).limit(20))).scalars().all()
        whales = (await session.execute(select(Event).where(Event.event_type == 'whale_transfer').order_by(Event.created_at.desc()).limit(20))).scalars().all()
    return {'health': await health(), 'signals': [d.__dict__ for d in decisions], 'whales': [e.__dict__ for e in whales]}

@app.get('/', response_class=HTMLResponse)
async def dashboard(request: Request, _: str = Depends(require_dashboard_auth)):
    return templates.TemplateResponse('dashboard.html', {'request': request, 'settings': settings, 'engine': engine})
