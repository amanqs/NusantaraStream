# ==============================================================================
#  🇮🇩 Nusantara Stream - Telegram Music & Video Streaming Bot
# ==============================================================================
#  Author   : Amang (@BukanDevelopers)
#  GitHub   : https://github.com/amanqs
#  Project  : Nusantara Stream Telegram Bot
#  License  : GNU General Public License v3.0
# ==============================================================================

import asyncio
import logging

try:
    from kurigram import Client, filters
    from kurigram.types import Message, LinkPreviewOptions
    from kurigram.errors import FloodWait, MessageNotModified
except ImportError:
    from pyrogram import Client, filters
    from pyrogram.types import Message, LinkPreviewOptions
    from pyrogram.errors import FloodWait, MessageNotModified

from config import Config
from utils.formatters import format_now_playing, get_clean_youtube_thumbnail
from utils.keyboards import get_control_panel
from utils.queue import queue_manager
from utils.rich_parser import RichParser

logger = logging.getLogger("NusantaraStream.NowPlaying")


@Client.on_message(filters.command(["np", "nowplaying"]) & ~filters.forwarded)
async def now_playing_command(client: Client, message: Message):
    """Menampilkan status lagu yang sedang diputar beserta visual Rich Message Table & Thumbnail Preview."""
    chat_id = message.chat.id
    current = queue_manager.get_current_track(chat_id)

    if not current:
        return await RichParser.reply(
            message,
            "❌ *Tidak ada musik atau video yang sedang diputar di grup ini.*"
        )

    text = format_now_playing(
        track=current,
        current_sec=current.elapsed_seconds,
        is_paused=queue_manager.is_paused(chat_id),
        is_looping=queue_manager.is_loop_enabled(chat_id),
        volume=queue_manager.get_volume(chat_id),
        is_muted=queue_manager.is_muted(chat_id),
    )
    markup = get_control_panel(
        chat_id=chat_id,
        is_paused=queue_manager.is_paused(chat_id),
        is_looping=queue_manager.is_loop_enabled(chat_id),
        is_muted=queue_manager.is_muted(chat_id),
    )

    clean_thumb = get_clean_youtube_thumbnail(current.url, getattr(current, "thumbnail", None))
    preview_url = clean_thumb or current.url
    preview_opts = LinkPreviewOptions(
        is_disabled=False,
        url=preview_url,
        prefer_large_media=True,
        show_above_text=True,
    ) if preview_url else None

    sent_msg = await RichParser.reply(
        message,
        text,
        reply_markup=markup,
        link_preview_options=preview_opts,
    )

    queue_manager.set_now_playing_msg(chat_id, sent_msg.id)


async def live_progress_updater(client: Client):
    """Background task untuk memperbarui status Now Playing secara periodik & aman dari FloodWait."""
    logger.info("Live progress updater background worker dimulai.")
    while True:
        try:
            active_chats = queue_manager.get_active_chats()
            for chat_id in active_chats:
                current = queue_manager.get_current_track(chat_id)
                msg_id = queue_manager.get_now_playing_msg(chat_id)

                # Update hanya jika lagu berjalan, bukan live stream, dan memenuhi rate limiter (25 detik)
                if (
                    current
                    and not current.is_live
                    and msg_id
                    and not queue_manager.is_paused(chat_id)
                ):
                    if queue_manager.can_update_ui(chat_id, interval=25.0):
                        text = format_now_playing(
                            track=current,
                            current_sec=current.elapsed_seconds,
                            is_paused=False,
                            is_looping=queue_manager.is_loop_enabled(chat_id),
                            volume=queue_manager.get_volume(chat_id),
                            is_muted=queue_manager.is_muted(chat_id),
                        )
                        markup = get_control_panel(
                            chat_id=chat_id,
                            is_paused=False,
                            is_looping=queue_manager.is_loop_enabled(chat_id),
                            is_muted=queue_manager.is_muted(chat_id),
                        )

                        try:
                            # Coba edit text jika pesan berbasis teks
                            await client.edit_message_text(
                                chat_id=chat_id,
                                message_id=msg_id,
                                rich_message=RichParser.get_input_rich_message(text),
                                reply_markup=markup,
                            )
                        except FloodWait as e:
                            # Backoff agar tidak mencoba mengedit selama periode FloodWait
                            import time
                            queue_manager._last_ui_update[chat_id] = time.time() + e.value + 5.0
                        except MessageNotModified:
                            pass
                        except Exception:
                            try:
                                await client.edit_message_reply_markup(
                                    chat_id=chat_id,
                                    message_id=msg_id,
                                    reply_markup=markup,
                                )
                            except Exception:
                                pass

            await asyncio.sleep(10)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error di background live updater: {e}")
            await asyncio.sleep(15)
