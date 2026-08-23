# ==============================================================================
#  🇮🇩 Nusantara Stream - Telegram Music & Video Streaming Bot
# ==============================================================================
#  Author   : Amang (@BukanDevelopers)
#  GitHub   : https://github.com/amanqs
#  Project  : Nusantara Stream Telegram Bot
#  License  : GNU General Public License v3.0
# ==============================================================================

import aiohttp
import logging
import re

try:
    from kurigram import Client, filters
    from kurigram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
    from kurigram.enums import ParseMode
except ImportError:
    from pyrogram import Client, filters
    from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
    from pyrogram.enums import ParseMode

from config import Config
from utils.queue import queue_manager
from utils.formatters import clean_markdown
from utils.rich_parser import RichParser
from utils.keyboards import resolve_style, ButtonStyle

logger = logging.getLogger("NusantaraStream.Lyrics")

# Cache lirik sementara: query -> {title, artist, lyrics}
LYRICS_CACHE: dict[str, dict] = {}


def clean_track_title(title: str) -> str:
    """Membersihkan judul YouTube dari tag-tag pengganggu agar pencarian lirik lebih akurat."""
    # Hapus teks dalam tanda kurung / kurung siku seperti (Official Video), [MV], dll.
    cleaned = re.sub(r"[\(\[].*?(official|video|audio|lyric|mv|hd|hq|remastered|feat|ft\.).*?[\)\]]", "", title, flags=re.IGNORECASE)
    cleaned = re.sub(r"[\(\[].*?[\)\]]", "", cleaned)
    cleaned = re.sub(r"[\|\-\_]", " ", cleaned)
    return " ".join(cleaned.split()).strip()


async def fetch_lyrics(query: str) -> dict | None:
    """Mengambil lirik lagu dari LRCLIB API secara asinkron."""
    if not query:
        return None

    clean_q = clean_track_title(query)
    if clean_q in LYRICS_CACHE:
        return LYRICS_CACHE[clean_q]

    url = "https://lrclib.net/api/search"
    params = {"q": clean_q or query}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data and isinstance(data, list):
                        for item in data:
                            plain = item.get("plainLyrics")
                            if plain and plain.strip():
                                result = {
                                    "title": item.get("trackName", query),
                                    "artist": item.get("artistName", "Artis"),
                                    "lyrics": plain.strip(),
                                }
                                LYRICS_CACHE[clean_q] = result
                                return result
    except Exception as e:
        logger.debug(f"Fetch lyrics error for '{query}': {e}")
    return None


@Client.on_message(filters.command(["lyrics", "lirik"]) & ~filters.forwarded)
async def lyrics_command(client: Client, message: Message):
    """Handler perintah /lyrics untuk mencari dan menampilkan lirik lagu."""
    chat_id = message.chat.id
    query = None

    if len(message.command) > 1:
        query = message.text.split(None, 1)[1].strip()
    else:
        # Coba ambil lagu yang sedang diputar di voice chat grup
        current = queue_manager.get_current_track(chat_id)
        if current:
            query = current.title

    if not query:
        return await RichParser.reply(
            message,
            "ℹ️ **Cara Penggunaan:**\n"
            "> - Ketik `/lyrics [Judul Lagu]`\n"
            "> - Atau putar lagu di VC lalu ketik `/lyrics`"
        )

    status_msg = await RichParser.reply(message, f"🔍 *Mencari lirik untuk:* `{clean_markdown(query)}`...")

    data = await fetch_lyrics(query)
    if not data:
        return await RichParser.edit(
            status_msg,
            f"❌ *Lirik tidak ditemukan untuk:* `{clean_markdown(query)}`"
        )

    title = clean_markdown(data["title"]).replace("|", "\\|")
    artist = clean_markdown(data["artist"]).replace("|", "\\|")
    lyrics_text = data["lyrics"]

    # Potong jika terlalu panjang untuk batas pesan Telegram (maks 4096 karakter)
    if len(lyrics_text) > 3200:
        lyrics_display = lyrics_text[:3200] + "\n\n... *(Lirik dipotong karena batas karakter)*"
    else:
        lyrics_display = lyrics_text

    card = (
        f"| 📜 Lirik Lagu: {title} |\n"
        f"|:---:|\n"
        f"| Artis: {artist} |\n\n"
        f"```text\n{lyrics_display}\n```\n\n"
        f"| 🤖 Nusantara Stream Engine 🤖 |\n"
        f"|:---:|\n"
        f"| |"
    )

    markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🗑 Tutup Lirik",
                    callback_data="help:close",
                    style=ButtonStyle.DANGER,
                )
            ]
        ]
    )

    await RichParser.edit(status_msg, card, reply_markup=markup)
