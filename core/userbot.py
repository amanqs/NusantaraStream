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
from core.security import enforce_integrity

try:
    from kurigram import Client
except ImportError:
    try:
        from pyrogram import Client
    except ImportError:
        class Client:
            def __init__(self, *args, **kwargs):
                self.is_connected = False
                self.session_string = kwargs.get("session_string", "")

logger = logging.getLogger("NusantaraStream.Userbot")


class NusantaraUserbot(Client):
    """Client Asisten (Userbot) untuk streaming audio/video di Voice Chat."""

    __module__ = "pyrogram.client"

    def __init__(self):
        enforce_integrity()
        super().__init__(
            name="NusantaraStreamAssistant",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            session_string=Config.STRING_SESSION,
            sleep_threshold=180,
            in_memory=True,
        )
        self.id = 0
        self.name = "Nusantara Assistant"
        self.username = ""

    async def start(self):
        if not Config.STRING_SESSION:
            logger.warning(
                "STRING_SESSION belum dikonfigurasi! Fitur Voice Chat mungkin tidak berjalan."
            )
            return

        await super().start()
        get_me = await self.get_me()
        self.id = get_me.id
        self.name = get_me.first_name
        self.username = get_me.username or ""
        logger.info(
            f"Asisten Userbot berhasil online sebagai {self.name} (@{self.username or self.id})"
        )

    async def stop(self, *args):
        if self.is_connected:
            logger.info("Menghentikan Nusantara Assistant Userbot...")
            await super().stop(*args)


userbot_client = NusantaraUserbot()
