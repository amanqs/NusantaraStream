# ==============================================================================
#  🇮🇩 Nusantara Stream - Telegram Music & Video Streaming Bot
# ==============================================================================
#  Author   : Amang (@BukanDevelopers)
#  GitHub   : https://github.com/amanqs
#  Project  : Nusantara Stream Telegram Bot
#  License  : GNU General Public License v3.0
# ==============================================================================

import logging
from typing import Optional

try:
    from kurigram import Client
    from kurigram.types import Message, User, Chat, LinkPreviewOptions
except ImportError:
    from pyrogram import Client
    from pyrogram.types import Message, User, Chat, LinkPreviewOptions

from config import Config
from utils.formatters import clean_markdown, get_readable_time, get_clean_youtube_thumbnail
from utils.rich_parser import RichParser
from utils.queue import TrackInfo

logger = logging.getLogger("NusantaraStream.LogHelper")


async def send_start_log(client: Client, message: Message):
    """Mengirim log ke LOG_GROUP_ID saat pengguna memulai (/start) bot."""
    if not Config.LOG_GROUP_ID:
        return

    try:
        user = message.from_user
        chat = message.chat

        user_name = clean_markdown(user.first_name if user else "Pengguna").replace("|", "\\|")
        user_id = user.id if user else 0
        username = f"@{user.username}" if (user and user.username) else "Tidak Ada"

        chat_type_str = "👤 Pesan Pribadi (Private)"
        chat_id_str = f"`{chat.id}`"
        if chat.type.value in ("group", "supergroup"):
            chat_title = clean_markdown(chat.title or "Grup").replace("|", "\\|")
            chat_type_str = f"👥 Grup: `{chat_title}`"
        elif chat.type.value == "channel":
            chat_title = clean_markdown(chat.title or "Channel").replace("|", "\\|")
            chat_type_str = f"📢 Saluran: `{chat_title}`"

        log_card = (
            "| 🚀 Log Pengguna /start Bot |\n"
            "|:---:|\n"
            "| Aktivitas pengguna memulai interaksi bot |\n\n"
            "| Parameter | Detail Informasi |\n"
            "|:---|:---|\n"
            f"| 👤 Pengguna | [{user_name}](tg://user?id={user_id}) (`{user_id}`) |\n"
            f"| 🏷️ Username | {username} |\n"
            f"| 💬 Tipe Obrolan | {chat_type_str} |\n"
            f"| 🆔 ID Obrolan | {chat_id_str} |\n\n"
            "| 🤖 Nusantara Stream Logger 🤖 |\n"
            "|:---:|\n"
            "| |"
        )

        await RichParser.send(
            client,
            chat_id=Config.LOG_GROUP_ID,
            text=log_card,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
    except Exception as e:
        logger.debug(f"Gagal mengirim start log ke grup: {e}")


async def send_stream_log(
    client: Client,
    chat_or_id,
    title_or_track=None,
    track: Optional[TrackInfo] = None,
    is_radio: bool = False,
    is_video: bool = False,
    **kwargs,
):
    """Mengirim log ke LOG_GROUP_ID saat pemutaran musik/video/radio/TV dimulai di Voice Chat."""
    if not Config.LOG_GROUP_ID:
        return

    try:
        # Resolusi parameter fleksibel (chat object vs chat_id)
        if hasattr(chat_or_id, "id"):
            chat_id = chat_or_id.id
            chat_title = getattr(chat_or_id, "title", "Voice Chat") or "Voice Chat"
            actual_track = title_or_track if isinstance(title_or_track, TrackInfo) else track
        else:
            chat_id = int(chat_or_id)
            if isinstance(title_or_track, str):
                chat_title = title_or_track
                actual_track = track
            else:
                chat_title = "Voice Chat"
                actual_track = title_or_track if isinstance(title_or_track, TrackInfo) else track

        if not actual_track:
            return

        clean_title = clean_markdown(actual_track.title).replace("|", "\\|")
        clean_req = clean_markdown(actual_track.requested_by_name or "Pengguna").replace("|", "\\|")
        req_id = actual_track.requested_by_id or 0
        clean_chat = clean_markdown(chat_title or "Voice Chat").replace("|", "\\|")

        is_tv_stream = (is_video or actual_track.is_video) and (actual_track.is_live or "iptv" in str(actual_track.channel).lower() or ".m3u8" in str(actual_track.url).lower())

        if is_radio:
            header_title = "📻 Log Siaran Radio Aktif"
            header_desc = "Siaran radio nasional dimulai di obrolan suara"
            media_label = "📻 Saluran Radio"
            stream_type = "📻 Radio 24/7 Nasional"
            dur_str = "🔴 Live 24/7"
            title_display = f"`{clean_title}`"
            media_part = ""
        elif is_tv_stream:
            header_title = "📺 Log Siaran Live TV & IPTV Aktif"
            header_desc = "Siaran televisi langsung dimulai di obrolan suara"
            media_label = "📺 Saluran TV"
            stream_type = "📺 Live TV / IPTV 720p HD"
            dur_str = "🔴 Siaran Langsung (Live)"
            title_display = f"`{clean_title}`"
            media_part = ""
        elif is_video or actual_track.is_video:
            header_title = "🎬 Log Pemutaran Video Aktif"
            header_desc = "Pemutaran video HD dimulai di obrolan suara"
            media_label = "🎬 Judul Video"
            stream_type = "🎬 Video HD 720p"
            dur_str = "🔴 Live" if actual_track.is_live else get_readable_time(actual_track.duration)
            title_display = f"[{clean_title}]({actual_track.url})" if actual_track.url.startswith("http") else f"`{clean_title}`"
            clean_thumb = get_clean_youtube_thumbnail(actual_track.url, getattr(actual_track, "thumbnail", None))
            media_part = f"![]({clean_thumb})\n\n" if clean_thumb else ""
        else:
            header_title = "🎵 Log Pemutaran Streaming Aktif"
            header_desc = "Pemutaran media musik dimulai di obrolan suara"
            media_label = "💿 Judul Lagu"
            stream_type = "🎵 Audio HQ 320kbps"
            dur_str = "🔴 Live" if actual_track.is_live else get_readable_time(actual_track.duration)
            title_display = f"[{clean_title}]({actual_track.url})" if actual_track.url.startswith("http") else f"`{clean_title}`"
            clean_thumb = get_clean_youtube_thumbnail(actual_track.url, getattr(actual_track, "thumbnail", None))
            media_part = f"![]({clean_thumb})\n\n" if clean_thumb else ""

        log_card = (
            f"{media_part}"
            f"| {header_title} |\n"
            f"|:---:|\n"
            f"| {header_desc} |\n\n"
            f"| Parameter | Detail Informasi |\n"
            f"|:---|:---|\n"
            f"| {media_label} | {title_display} |\n"
            f"| 🎬 Format Stream | {stream_type} |\n"
            f"| ⏱ Total Durasi | `{dur_str}` |\n"
            f"| 👤 Diminta oleh | [{clean_req}](tg://user?id={req_id}) (`{req_id}`) |\n"
            f"| 👥 Obrolan Suara | `{clean_chat}` (`{chat_id}`) |\n\n"
            f"| 🤖 Nusantara Stream Logger 🤖 |\n"
            f"|:---:|\n"
            f"| |"
        )

        await RichParser.send(
            client,
            chat_id=Config.LOG_GROUP_ID,
            text=log_card,
        )
    except Exception as e:
        logger.debug(f"Gagal mengirim stream log ke grup: {e}")
