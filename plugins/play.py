# ==============================================================================
#  🇮🇩 Nusantara Stream - Telegram Music & Video Streaming Bot
# ==============================================================================
#  Author   : Amang (@BukanDevelopers)
#  GitHub   : https://github.com/amanqs
#  Project  : Nusantara Stream Telegram Bot
#  License  : GNU General Public License v3.0
# ==============================================================================

import time
import logging
import os

try:
    from kurigram import Client, filters
    from kurigram.types import Message, CallbackQuery, InputMediaPhoto, LinkPreviewOptions
    from kurigram.enums import ChatType, ParseMode
except ImportError:
    from pyrogram import Client, filters
    from pyrogram.types import Message, CallbackQuery, InputMediaPhoto, LinkPreviewOptions
    from pyrogram.enums import ChatType, ParseMode

from config import Config
from utils.call_manager import call_manager
from utils.formatters import (
    format_now_playing,
    format_single_search_result,
    format_search_results,
    format_download_progress_card,
    get_clean_youtube_thumbnail,
    get_readable_time,
    clean_markdown,
)
from utils.keyboards import (
    get_control_panel,
    get_search_carousel_keyboard,
    get_search_keyboard,
)
from utils.queue import queue_manager, TrackInfo
from utils.ytdl import ytdl_helper
from utils.decorators import bot_admin_check
from utils.rich_parser import RichParser
from utils.card_generator import get_now_playing_card_path
from utils.database import db

logger = logging.getLogger("NusantaraStream.Play")

# Cache pencarian sementara: f"{chat_id}_{user_id}" -> list[dict]
SEARCH_CACHE: dict[str, list[dict]] = {}


@Client.on_message(
    filters.command(["play", "vplay", "cplay", "stream", "vstream"])
    & ~filters.forwarded
)
@bot_admin_check
async def play_command_handler(client: Client, message: Message):
    """Handler utama untuk perintah /play, /vplay, dan streaming."""
    chat = message.chat
    user = message.from_user
    user_id = user.id if user else 0
    user_name = clean_markdown(user.first_name if user else "Pengguna")

    if user:
        await db.add_served_user(user.id, user.first_name, user.username)
    if chat.type != ChatType.PRIVATE:
        await db.add_served_chat(chat.id, chat.title, str(chat.type))

    if chat.type == ChatType.PRIVATE:
        return await RichParser.reply(
            message,
            "⚠️ *Fitur pemutar musik hanya dapat digunakan di Grup atau Channel Telegram.*\n\n"
            "> Silakan tambahkan bot ke grup Anda untuk mulai memutar lagu!",
            reply_markup=get_control_panel(chat.id),
        )

    cmd = message.command[0].lower()
    is_video = "v" in cmd

    # 1. Kasus jika membalas (reply) ke file audio atau video Telegram
    reply = message.reply_to_message
    if reply and (reply.audio or reply.video or reply.document or reply.voice):
        media = (
            reply.audio or reply.video or reply.document or reply.voice
        )
        file_name = getattr(media, "file_name", None) or (
            "Telegram_Video.mp4" if reply.video else "Telegram_Audio.mp3"
        )
        file_size = getattr(media, "file_size", 0) or 0
        file_path = os.path.join(Config.TEMP_DIR, f"{reply.id}_{file_name}")

        init_card = format_download_progress_card(
            file_name=file_name,
            current_bytes=0,
            total_bytes=file_size,
        )
        status_msg = await RichParser.reply(
            message,
            init_card,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )

        start_time = time.time()
        last_edit_time = 0

        async def progress_callback(current, total):
            nonlocal last_edit_time
            now = time.time()
            if current == total or (now - last_edit_time >= 3.0):
                last_edit_time = now
                elapsed = max(0.1, now - start_time)
                speed = current / elapsed
                eta = int((total - current) / speed) if speed > 0 else 0
                card = format_download_progress_card(
                    file_name=file_name,
                    current_bytes=current,
                    total_bytes=total,
                    speed=speed,
                    eta=eta,
                )
                try:
                    await RichParser.edit(
                        status_msg,
                        card,
                        link_preview_options=LinkPreviewOptions(is_disabled=True),
                    )
                except Exception:
                    pass

        try:
            downloaded_file = await reply.download(
                file_name=file_path,
                progress=progress_callback,
            )
            duration = getattr(media, "duration", 0) or 0
            title = getattr(media, "title", None) or file_name

            track = TrackInfo(
                title=title,
                url=f"https://t.me/{chat.username or 'c'}/{reply.id}",
                stream_url=downloaded_file,
                duration=duration,
                channel=user_name,
                requested_by_id=user_id,
                requested_by_name=user_name,
                is_video=is_video or bool(reply.video),
                file_path=downloaded_file,
            )

            await process_track_playback(client, message, status_msg, track)
            return
        except Exception as e:
            logger.error(f"Gagal memproses file media Telegram: {e}")
            return await RichParser.edit(
                status_msg,
                f"❌ **Gagal memutar file:** `{clean_markdown(str(e))}`"
            )

    # Cek apakah ada argumen query setelah perintah
    if len(message.command) < 2:
        return await RichParser.reply(
            message,
            "ℹ️ **Format Perintah:**\n"
            f"> - `/{cmd} [Judul Lagu / URL YouTube]`\n"
            f"> - Balas pesan audio/video dengan `/{cmd}`"
        )

    query = message.text.split(None, 1)[1].strip()

    # 2. Kasus jika query adalah tautan Spotify
    if ytdl_helper.is_spotify(query):
        status_msg = await RichParser.reply(
            message,
            "🟢 *Mengambil metadata lagu dari Spotify...*"
        )
        try:
            sp_tracks = await ytdl_helper.resolve_spotify(query)
            if not sp_tracks:
                return await RichParser.edit(
                    status_msg,
                    "❌ *Tidak dapat mengambil detail lagu dari tautan Spotify tersebut.*"
                )

            sp_item = sp_tracks[0]
            await RichParser.edit(
                status_msg,
                f"🟢 *Spotify:* `{sp_item['title']}` - `{sp_item['artist']}`\n"
                "🔍 *Mencari audio streaming berkualitas tinggi...*"
            )
            track = await ytdl_helper.extract_stream(
                query_or_url=sp_item["query"],
                is_video=is_video,
                requester_id=user_id,
                requester_name=user_name,
            )
            if not track:
                return await RichParser.edit(
                    status_msg,
                    f"❌ *Gagal menemukan streaming untuk:* `{sp_item['title']}`"
                )

            track.channel = f"Spotify • {sp_item['artist']}"
            if sp_item.get("thumbnail") and not track.thumbnail:
                track.thumbnail = sp_item["thumbnail"]

            await process_track_playback(client, message, status_msg, track)
            return
        except Exception as e:
            logger.error(f"Error saat resolve Spotify: {e}")
            return await RichParser.edit(
                status_msg,
                f"❌ **Terjadi kesalahan Spotify:** `{clean_markdown(str(e))}`"
            )

    # 3. Kasus jika query adalah URL langsung (YouTube / SoundCloud / Direct Link)
    if ytdl_helper.is_url(query):
        status_msg = await RichParser.reply(
            message,
            "🔍 *Memproses tautan media langsung...*"
        )
        try:
            track = await ytdl_helper.extract_stream(
                query_or_url=query,
                is_video=is_video,
                requester_id=user_id,
                requester_name=user_name,
            )
            if not track:
                return await RichParser.edit(
                    status_msg,
                    "❌ *Tidak dapat mengekstrak media dari URL tersebut. Pastikan link dapat diakses.*"
                )

            await process_track_playback(client, message, status_msg, track)
            return
        except Exception as e:
            logger.error(f"Error saat extract URL: {e}")
            return await RichParser.edit(
                status_msg,
                f"❌ **Terjadi kesalahan:** `{clean_markdown(str(e))}`"
            )

    # 3. Kasus jika query berupa kata kunci pencarian (YouTube Carousel)
    status_msg = await RichParser.reply(
        message,
        f"🔍 *Mencari di YouTube:* `{clean_markdown(query)}`..."
    )
    try:
        results = await ytdl_helper.search_youtube(
            query=query, limit=Config.SEARCH_LIMIT
        )
        if not results:
            return await RichParser.edit(
                status_msg,
                "❌ *Tidak ada hasil yang ditemukan untuk kata kunci tersebut.*"
            )

        # Simpan hasil pencarian ke cache
        cache_key = f"{chat.id}_{user_id}"
        SEARCH_CACHE[cache_key] = results

        # Tampilkan hasil ke-1 secara interaktif dengan thumbnail dan navigasi geser
        first_item = results[0]
        caption_text = format_single_search_result(first_item, 0, len(results))
        markup = get_search_carousel_keyboard(0, len(results), user_id)

        try:
            await status_msg.delete()
        except Exception:
            pass

        preview_url = first_item.get("url") or first_item.get("thumbnail")
        preview_opts = LinkPreviewOptions(
            is_disabled=False,
            url=preview_url,
            prefer_large_media=True,
            show_above_text=True,
        ) if preview_url else None

        await RichParser.reply(
            message,
            caption_text,
            reply_markup=markup,
            link_preview_options=preview_opts,
        )
    except Exception as e:
        logger.error(f"Error search youtube: {e}")
        await RichParser.edit(
            status_msg,
            f"❌ **Gagal mencari:** `{clean_markdown(str(e))}`"
        )


async def process_track_playback(
    client: Client, message: Message, status_msg: Message, track: TrackInfo
):
    """Memproses apakah lagu langsung diputar atau dimasukkan ke antrean."""
    chat_id = message.chat.id
    current_playing = queue_manager.get_current_track(chat_id)

    # Jika sedang ada lagu yang diputar, masukkan ke antrean
    if current_playing:
        pos = queue_manager.add_to_queue(chat_id, track)
        media_type = "🎬 Video" if track.is_video else "🎵 Audio"
        dur = "🔴 Live" if track.is_live else get_readable_time(track.duration)
        clean_t = clean_markdown(track.title).replace("|", "\\|")
        clean_req = clean_markdown(track.requested_by_name).replace("|", "\\|")

        clean_thumb = get_clean_youtube_thumbnail(track.url, getattr(track, "thumbnail", None))
        media_part = f"![]({clean_thumb})\n\n" if clean_thumb else ""
        queue_card = (
            f"{media_part}"
            f"| ✅ Ditambahkan Ke Antrean #{pos} |\n"
            f"|:---:|\n"
            f"| |\n\n"
            f"| Parameter | Detail Informasi |\n"
            f"|:---|:---|\n"
            f"| 💿 Judul Media | [{clean_t}]({track.url}) |\n"
            f"| ⏱ Durasi | {dur} |\n"
            f"| 👤 Diminta oleh | {clean_req} |\n"
            f"| 🎬 Tipe Format | {media_type} |\n\n"
            f"| 🤖 Nusantara Stream 🤖 |\n"
            f"|:---:|\n"
            f"| |"
        )
        preview_opts = LinkPreviewOptions(
            is_disabled=False,
            url=clean_thumb or track.url,
            prefer_large_media=True,
            show_above_text=True,
        ) if (clean_thumb or track.url) else None

        await RichParser.edit(status_msg, queue_card, link_preview_options=preview_opts)
        return

    # Jika belum ada yang diputar, mulai pemutaran di Voice Chat
    try:
        await call_manager.play_stream(chat_id, track)
        np_text = format_now_playing(
            track=track,
            current_sec=0,
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
            if status_msg:
                await status_msg.delete()
        except Exception:
            pass

        clean_thumb = get_clean_youtube_thumbnail(track.url, getattr(track, "thumbnail", None))
        preview_url = clean_thumb or track.url
        preview_opts = LinkPreviewOptions(
            is_disabled=False,
            url=preview_url,
            prefer_large_media=True,
            show_above_text=True,
        ) if preview_url else None

        sent_msg = await RichParser.send(
            client,
            chat_id=chat_id,
            text=np_text,
            reply_markup=markup,
            link_preview_options=preview_opts,
        )

        queue_manager.set_now_playing_msg(chat_id, sent_msg.id)
    except Exception as e:
        logger.error(f"Gagal memutar di Voice Chat: {e}")
        await RichParser.edit(
            status_msg,
            f"❌ **Gagal memutar lagu di Voice Chat!**\n\n"
            f"> *Pastikan Voice Chat di grup sudah diaktifkan dan akun asisten sudah bergabung di grup.*\n\n"
            f"**Detail Error:** `{clean_markdown(str(e))}`"
        )


@Client.on_callback_query(filters.regex(r"^search_nav:(\d+):(\d+)"))
async def search_carousel_navigation(client: Client, query: CallbackQuery):
    """Handler navigasi geser (carousel) hasil pencarian YouTube."""
    data = query.data.split(":")
    idx = int(data[1])
    requester_id = int(data[2])

    user_id = query.from_user.id if query.from_user else 0
    chat_id = query.message.chat.id

    # Cek hak user yang menggeser
    if user_id != requester_id and user_id not in Config.SUDO_USERS:
        return await query.answer(
            "⚠️ Hanya pengguna yang melakukan pencarian yang dapat menggeser hasil ini.",
            show_alert=True,
        )

    cache_key = f"{chat_id}_{requester_id}"
    results = SEARCH_CACHE.get(cache_key)

    if not results or idx < 0 or idx >= len(results):
        return await query.answer(
            "❌ Hasil pencarian telah kadaluarsa.",
            show_alert=True,
        )

    item = results[idx]
    caption_text = format_single_search_result(item, idx, len(results))
    markup = get_search_carousel_keyboard(idx, len(results), requester_id)

    preview_url = item.get("url") or item.get("thumbnail")
    preview_opts = LinkPreviewOptions(
        is_disabled=False,
        url=preview_url,
        prefer_large_media=True,
        show_above_text=True,
    ) if preview_url else None

    try:
        if query.message.photo:
            try:
                await query.message.delete()
            except Exception:
                pass
            await RichParser.send(
                client,
                chat_id=chat_id,
                text=caption_text,
                reply_markup=markup,
                link_preview_options=preview_opts,
            )
        else:
            await RichParser.edit(
                query,
                caption_text,
                reply_markup=markup,
                link_preview_options=preview_opts,
            )
    except Exception as e:
        logger.debug(f"Error navigation carousel: {e}")

    await query.answer()


@Client.on_callback_query(filters.regex(r"^play_select:(\d+):(\d+):([av])"))
async def search_play_select_callback(client: Client, query: CallbackQuery):
    """Handler pemilihan format Audio / Video untuk diputar di Voice Chat."""
    data = query.data.split(":")
    idx = int(data[1])
    requester_id = int(data[2])
    is_video = data[3] == "v"

    user_id = query.from_user.id if query.from_user else 0
    chat_id = query.message.chat.id

    # Cek hak user
    if user_id != requester_id and user_id not in Config.SUDO_USERS:
        return await query.answer(
            "⚠️ Hanya pengguna yang melakukan pencarian yang dapat memutar lagu ini.",
            show_alert=True,
        )

    cache_key = f"{chat_id}_{requester_id}"
    results = SEARCH_CACHE.get(cache_key)

    if not results or idx >= len(results):
        return await query.answer(
            "❌ Hasil pencarian telah kadaluarsa. Silakan cari kembali.",
            show_alert=True,
        )

    selected_item = results[idx]
    sel_title = clean_markdown(selected_item["title"])
    media_label = "Video HD 🎬" if is_video else "Audio HQ 🎵"

    # Perbarui pesan status
    loading_text = f"⏳ *Memproses {media_label}:* **{sel_title}**..."
    try:
        if query.message.photo:
            await query.message.edit_caption(
                caption=loading_text,
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await RichParser.edit(query, loading_text)
    except Exception:
        pass

    try:
        track = await ytdl_helper.extract_stream(
            query_or_url=selected_item["url"],
            is_video=is_video,
            requester_id=user_id,
            requester_name=query.from_user.first_name if query.from_user else "Pengguna",
        )

        if not track:
            err_txt = "❌ *Gagal mengekstrak streaming dari lagu yang dipilih.*"
            if query.message.photo:
                return await query.message.edit_caption(
                    caption=err_txt, parse_mode=ParseMode.MARKDOWN
                )
            return await RichParser.edit(query, err_txt)

        # Bersihkan cache pencarian
        SEARCH_CACHE.pop(cache_key, None)

        await process_track_playback(
            client=client,
            message=query.message,
            status_msg=query.message,
            track=track,
        )
    except Exception as e:
        logger.error(f"Error proses play select: {e}")
        err_msg = f"❌ **Error:** `{clean_markdown(str(e))}`"
        if query.message.photo:
            await query.message.edit_caption(
                caption=err_msg, parse_mode=ParseMode.MARKDOWN
            )
        else:
            await RichParser.edit(query, err_msg)


@Client.on_callback_query(filters.regex(r"^play_search:(\d+):(\d+):([av])"))
async def search_selection_callback(client: Client, query: CallbackQuery):
    """Handler backward compatibility pemilihan lagu."""
    return await search_play_select_callback(client, query)


@Client.on_callback_query(filters.regex(r"^cancel_search:(\d+)"))
async def cancel_search_callback(client: Client, query: CallbackQuery):
    """Handler pembatalan menu pencarian."""
    requester_id = int(query.data.split(":")[1])
    user_id = query.from_user.id if query.from_user else 0

    if user_id != requester_id and user_id not in Config.SUDO_USERS:
        return await query.answer(
            "⚠️ Anda tidak memiliki izin untuk membatalkan pencarian ini.",
            show_alert=True,
        )

    chat_id = query.message.chat.id
    SEARCH_CACHE.pop(f"{chat_id}_{requester_id}", None)

    try:
        await query.message.delete()
    except Exception:
        pass
    await query.answer("Pencarian dibatalkan.")
