from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from ..config import Settings

class TelegramService:
    def __init__(self, settings: Settings, status_provider, stop_provider, resume_provider):
        self.settings = settings
        self.status_provider = status_provider
        self.stop_provider = stop_provider
        self.resume_provider = resume_provider
        self.application: Application | None = None

    def _authorized(self, update: Update) -> bool:
        return bool(self.settings.telegram_chat_id and update.effective_chat and str(update.effective_chat.id) == self.settings.telegram_chat_id)

    async def send(self, text: str) -> None:
        if not self.settings.telegram_bot_token or not self.settings.telegram_chat_id:
            return
        if self.application is None:
            self.application = Application.builder().token(self.settings.telegram_bot_token).build()
        await self.application.bot.send_message(chat_id=self.settings.telegram_chat_id, text=text)

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update): return
        await update.message.reply_text(await self.status_provider())

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update): return
        await update.message.reply_text('JUNO CORE ENGINE aktif. /status ile durum, /stop ile işlem katmanını durdurma talimatı alınır.')

    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update): return
        await self.stop_provider()
        await update.message.reply_text('🤖 JUNO: Çalışma döngüleri durduruldu.')

    async def resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update): return
        await self.resume_provider()
        await update.message.reply_text('🤖 JUNO: Çalışma döngüleri yeniden başlatıldı.')

    def build(self) -> Application | None:
        if not self.settings.telegram_bot_token:
            return None
        app = Application.builder().token(self.settings.telegram_bot_token).build()
        app.add_handler(CommandHandler('start', self.start))
        app.add_handler(CommandHandler('status', self.status))
        app.add_handler(CommandHandler('stop', self.stop))
        app.add_handler(CommandHandler('run', self.resume))
        return app
