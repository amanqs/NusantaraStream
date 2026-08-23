# ==============================================================================
#  🇮🇩 Nusantara Stream - Telegram Music & Video Streaming Bot
# ==============================================================================
#  Author   : Amang (@BukanDevelopers)
#  GitHub   : https://github.com/amanqs
#  Project  : Nusantara Stream Telegram Bot
#  License  : GNU General Public License v3.0
# ==============================================================================

import logging
from config import Config
from core.security import enforce_integrity, get_root_creator_id

try:
    from kurigram import Client
    from kurigram.enums import ParseMode
except ImportError:
    try:
        from pyrogram import Client
        from pyrogram.enums import ParseMode
    except ImportError:
        class Client:
            def __init__(self, *args, **kwargs):
                self.is_connected = False
                self.username = ""
                self.id = 0
                self.name = ""

        class ParseMode:
            HTML = "html"
            MARKDOWN = "markdown"

logger = logging.getLogger("NusantaraStream.Bot")


class NusantaraBot(Client):
    """Client Bot Utama Nusantara Stream berbasis Kurigram."""

    def __init__(self):
        enforce_integrity()
        super().__init__(
            name="NusantaraStreamBot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            plugins=dict(root="plugins"),
            parse_mode=ParseMode.MARKDOWN,
            sleep_threshold=180,
            max_concurrent_transmissions=4,
            in_memory=False,
        )
        self.id = 0
        self.name = Config.BOT_NAME
        self.username = Config.BOT_USERNAME

    async def start(self):
        await super().start()
        get_me = await self.get_me()
        self.id = get_me.id
        self.name = get_me.first_name
        self.username = get_me.username or Config.BOT_USERNAME
        logger.info(f"Bot berhasil online sebagai @{self.username} (ID: {self.id})")

    async def stop(self, *args):
        logger.info("Menghentikan Nusantara Stream Bot...")
        await super().stop(*args)


bot_client = NusantaraBot()
