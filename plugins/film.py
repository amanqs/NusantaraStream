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
    from kurigram import Client, filters
    from kurigram.types import Message, CallbackQuery, LinkPreviewOptions
    from kurigram.enums import ChatType
except ImportError:
    from pyrogram import Client, filters
    from pyrogram.types import Message, CallbackQuery, LinkPreviewOptions
    from pyrogram.enums import ChatType

try:
    from kurigram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from kurigram.enums import ButtonStyle
except ImportError:
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from pyrogram.enums import ButtonStyle

from config import Config
from core.userbot import userbot_client
from utils.call_manager import call_manager
from utils.queue import queue_manager, TrackInfo
from utils.formatters import clean_markdown, get_readable_time, human_readable_size
from utils.keyboards import get_control_panel, resolve_style
from utils.rich_parser import RichParser
from utils.decorators import bot_admin_check
from utils.log_helper import send_stream_log

logger = logging.getLogger("NusantaraStream.Film")

# Channel sumber film (joinkan userbot ke channel ini)
FILM_CHANNEL_ID = -1001688942576

# Jumlah film per halaman di katalog
FILMS_PER_PAGE = 8

# Cache katalog dan pencarian film per sesi
FILM_CATALOG_CACHE: list[dict] = []          # daftar semua film dari channel
FILM_SEARCH_CACHE: dict[str, list[dict]] = {} # f"{chat_id}_{msg_id}" -> list[dict]


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

async def _fetch_film_catalog(force_refresh: bool = False) -> list[dict]:
    """Mengambil katalog film dari channel Telegram melalui userbot."""
    global FILM_CATALOG_CACHE
    if FILM_CATALOG_CACHE and not force_refresh:
        return FILM_CATALOG_CACHE

    films = []
    try:
        async for msg in userbot_client.get_chat_history(FILM_CHANNEL_ID, limit=500):
            media = msg.video or msg.document
            if not media:
                continue
            # Filter: hanya file video/dokumen yang kemungkinan film
            mime = getattr(media, "mime_type", "") or ""
            fname = getattr(media, "file_name", "") or ""
            if "video" not in mime and not any(
                fname.lower().endswith(ext) for ext in (".mp4", ".mkv", ".avi", ".mov", ".m4v", ".webm")
            ):
                continue

            caption = msg.caption or fname or "Film Tanpa Judul"
            # Ambil baris pertama caption sebagai judul
            title = caption.split("\n")[0].strip()[:80] or fname or "Film"

            films.append({
                "message_id": msg.id,
                "title": title,
                "file_id": media.file_id,
                "file_name": fname or "video.mp4",
                "file_size": getattr(media, "file_size", 0) or 0,
                "duration": getattr(media, "duration", 0) or 0,
                "mime_type": mime,
                "date": msg.date,
                "caption": caption[:300],
                "thumb": getattr(media.thumbs[0], "file_id", None) if getattr(media, "thumbs", None) else None,
            })
    except Exception as e:
        logger.error(f"Gagal mengambil katalog film dari channel: {e}")

    # Urutkan: film terbaru di atas
    films.sort(key=lambda x: x.get("date") or 0, reverse=True)
    FILM_CATALOG_CACHE = films
    return films


def _search_films(films: list[dict], query: str) -> list[dict]:
    """Filter film berdasarkan kata kunci pencarian."""
    q = query.lower().strip()
    if not q:
        return films
    return [
        f for f in films
        if q in f["title"].lower()
        or q in (f.get("caption") or "").lower()
        or q in (f.get("file_name") or "").lower()
    ]


def _format_film_catalog_card(page: int, total: int, total_pages: int, query: str = "") -> str:
    """Format kartu katalog bioskop."""
    page_info = f"`{page} / {total_pages}`"
    source_info = f"Hasil pencarian: `{clean_markdown(query)}`" if query else "Katalog Terbaru"
    return (
        "| 🎬 Nusantara Cinema — Bioskop Telegram |\n"
        "|:---:|\n"
        "| Tonton film langsung di Voice Chat Video grup |\n\n"
        "| Parameter | Detail |\n"
        "|:---|:---|\n"
        f"| 📂 Sumber | Channel Film Privat |\n"
        f"| 🎞 {source_info} | `{total}` Film Tersedia |\n"
        f"| 📄 Halaman | {page_info} |\n\n"
        "| 💡 Klik judul film di bawah untuk langsung memutarnya ke Voice Chat: |\n"
        "|:---:|\n"
        "| |"
    )


def _get_film_catalog_keyboard(
    films: list[dict],
    page: int,
    total_pages: int,
    query: str = "",
    search_key: str = "",
) -> InlineKeyboardMarkup:
    """Keyboard katalog film berhalaman dengan tombol navigasi."""
    start = (page - 1) * FILMS_PER_PAGE
    end = start + FILMS_PER_PAGE
    page_films = films[start:end]

    keyboard = []

    # Tombol per-film
    for i, film in enumerate(page_films):
        global_idx = start + i
        dur_str = f" [{get_readable_time(film['duration'])}]" if film.get("duration") else ""
        size_str = f" · {human_readable_size(film['file_size'])}" if film.get("file_size") else ""
        label = f"🎬 {film['title'][:36]}{dur_str}{size_str}"
        cb = f"film_play:{global_idx}:{search_key}" if search_key else f"film_play:{global_idx}:"
        keyboard.append([
            InlineKeyboardButton(label[:62], callback_data=cb, style=resolve_style(ButtonStyle.DEFAULT))
        ])

    # Navigasi halaman
    nav = []
    if page > 1:
        q_enc = f":{query}" if query else ":"
        nav.append(InlineKeyboardButton(
            "⬅️ Prev",
            callback_data=f"film_page:{page - 1}{q_enc}{search_key}",
            style=ButtonStyle.PRIMARY,
        ))
    nav.append(InlineKeyboardButton(
        f"📄 {page}/{total_pages}",
        callback_data="film_page_info",
        style=ButtonStyle.DEFAULT,
    ))
    if page < total_pages:
        q_enc = f":{query}" if query else ":"
        nav.append(InlineKeyboardButton(
            "Next ➡️",
            callback_data=f"film_page:{page + 1}{q_enc}{search_key}",
            style=ButtonStyle.PRIMARY,
        ))
    if nav:
        keyboard.append(nav)

    # Tombol Refresh & Tutup
    keyboard.append([
        InlineKeyboardButton("🔄 Refresh Katalog", callback_data="film_refresh", style=ButtonStyle.SUCCESS),
        InlineKeyboardButton("❌ Tutup", callback_data="film_close", style=ButtonStyle.DANGER),
    ])

    return InlineKeyboardMarkup(keyboard)


# ─────────────────────────────────────────────
#  COMMANDS
# ─────────────────────────────────────────────

@Client.on_message(filters.command(["film", "movie", "bioskop", "cinema"]) & ~filters.forwarded)
@bot_admin_check
async def film_command(client: Client, message: Message):
    """Handler /film — Katalog atau pencarian film dari channel privat."""
    chat = message.chat
    user = message.from_user

    if chat.type == ChatType.PRIVATE:
        return await RichParser.reply(
            message,
            "⚠️ *Fitur bioskop hanya dapat digunakan di Grup dengan Voice Chat aktif.*",
        )

    if not userbot_client or not getattr(userbot_client, "is_connected", False):
        return await RichParser.reply(
            message,
            "❌ Asisten Userbot belum terhubung. Pastikan `STRING_SESSION` sudah dikonfigurasi.",
        )

    args = message.text.split(None, 1) if message.text else []
    query = args[1].strip() if len(args) > 1 else ""

    status_msg = await RichParser.reply(
        message,
        f"| 🎬 Memuat Katalog Film... |\n|:---:|\n| {'Mencari: ' + clean_markdown(query) if query else 'Mengambil daftar film terbaru dari server...'} |",
    )

    # Ambil katalog (gunakan cache kecuali pertama kali)
    all_films = await _fetch_film_catalog()

    if query:
        films = _search_films(all_films, query)
        if not films:
            return await RichParser.edit(
                status_msg,
                f"❌ Tidak ditemukan film dengan kata kunci `{clean_markdown(query)}`.\n"
                f"Ketik `/film` untuk melihat katalog lengkap.",
            )
    else:
        films = all_films

    if not films:
        return await RichParser.edit(
            status_msg,
            "❌ Katalog film masih kosong atau channel tidak dapat dijangkau.\n"
            "Pastikan userbot sudah bergabung ke channel film.",
        )

    total = len(films)
    total_pages = max(1, (total + FILMS_PER_PAGE - 1) // FILMS_PER_PAGE)
    page = 1

    # Simpan cache pencarian agar callback bisa akses
    search_key = ""
    if query:
        search_key = f"{chat.id}_{message.id}"
        FILM_SEARCH_CACHE[search_key] = films

    text = _format_film_catalog_card(page, total, total_pages, query)
    markup = _get_film_catalog_keyboard(films, page, total_pages, query, search_key)

    await RichParser.edit(
        status_msg,
        text,
        reply_markup=markup,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    queue_manager.set_now_playing_msg(chat.id, status_msg.id)


# ─────────────────────────────────────────────
#  CALLBACKS — NAVIGASI HALAMAN
# ─────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^film_page:(\d+):?([^:]*):?(.*)$"))
async def film_page_callback(client: Client, query: CallbackQuery):
    """Navigasi halaman katalog film."""
    match = query.matches[0]
    page = int(match.group(1))
    raw_query = match.group(2) or ""
    search_key = match.group(3) or ""

    if search_key and search_key in FILM_SEARCH_CACHE:
        films = FILM_SEARCH_CACHE[search_key]
    else:
        films = await _fetch_film_catalog()
        search_key = ""

    total = len(films)
    total_pages = max(1, (total + FILMS_PER_PAGE - 1) // FILMS_PER_PAGE)
    page = max(1, min(page, total_pages))

    text = _format_film_catalog_card(page, total, total_pages, raw_query)
    markup = _get_film_catalog_keyboard(films, page, total_pages, raw_query, search_key)

    try:
        await RichParser.edit(
            query.message,
            text,
            reply_markup=markup,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
    except Exception:
        pass
    await query.answer()


@Client.on_callback_query(filters.regex(r"^film_refresh$"))
async def film_refresh_callback(client: Client, query: CallbackQuery):
    """Refresh katalog film (paksa ambil ulang dari channel)."""
    await query.answer("🔄 Memperbarui katalog film...", show_alert=False)
    films = await _fetch_film_catalog(force_refresh=True)
    total = len(films)
    total_pages = max(1, (total + FILMS_PER_PAGE - 1) // FILMS_PER_PAGE)
    text = _format_film_catalog_card(1, total, total_pages)
    markup = _get_film_catalog_keyboard(films, 1, total_pages)
    try:
        await RichParser.edit(
            query.message,
            text,
            reply_markup=markup,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
    except Exception:
        pass


@Client.on_callback_query(filters.regex(r"^film_page_info$"))
async def film_page_info_callback(client: Client, query: CallbackQuery):
    """Info halaman saat tombol nomor halaman diklik."""
    await query.answer("ℹ️ Gunakan tombol Prev / Next untuk berpindah halaman.", show_alert=False)


# ─────────────────────────────────────────────
#  CALLBACKS — PUTAR FILM
# ─────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^film_play:(\d+):(.*)$"))
async def film_play_callback(client: Client, query: CallbackQuery):
    """Callback untuk memilih dan memutar film ke Voice Chat."""
    film_idx = int(query.matches[0].group(1))
    search_key = query.matches[0].group(2) or ""

    chat = query.message.chat
    if chat.type == ChatType.PRIVATE:
        return await query.answer(
            "⚠️ Hanya dapat digunakan di grup dengan Voice Chat aktif!", show_alert=True
        )

    # Ambil data film
    if search_key and search_key in FILM_SEARCH_CACHE:
        films = FILM_SEARCH_CACHE[search_key]
    else:
        films = await _fetch_film_catalog()

    if film_idx >= len(films):
        return await query.answer("❌ Data film tidak ditemukan atau kadaluarsa.", show_alert=True)

    film = films[film_idx]
    user = query.from_user

    await query.answer(f"🎬 Memuat: {film['title'][:30]}...", show_alert=False)

    # Perbarui kartu jadi status loading
    loading_card = (
        "| 🎬 Menyiapkan Pemutaran Film... |\n"
        "|:---:|\n"
        f"| Mengalirkan **{clean_markdown(film['title'][:50])}** ke Voice Chat |\n\n"
        "| Proses | Status |\n"
        "|:---|:---|\n"
        "| 📥 Memuat file dari channel | ⏳ Harap tunggu... |\n"
        "| 🎬 Kualitas Stream | 720p HD Video + HQ Audio |"
    )
    try:
        await RichParser.edit(
            query.message,
            loading_card,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
    except Exception:
        pass

    try:
        # Siapkan TrackInfo dari file Telegram
        track = TrackInfo(
            title=film["title"],
            url=f"https://t.me/c/{str(FILM_CHANNEL_ID).replace('-100', '')}/{film['message_id']}",
            stream_url="",  # Akan menggunakan file_id
            duration=film.get("duration") or 0,
            video_url="",
            file_id=film["file_id"],
            thumbnail=None,
            requested_by_name=user.first_name if user else "Pengguna",
            requested_by_id=user.id if user else 0,
            channel="🎬 Nusantara Cinema",
            is_video=True,
            is_live=False,
        )

        # Minta userbot download file sementara
        loading_path_card = (
            "| 🎬 Menyiapkan Pemutaran Film... |\n"
            "|:---:|\n"
            f"| **{clean_markdown(film['title'][:50])}** |\n\n"
            "| Proses | Status |\n"
            "|:---|:---|\n"
            "| 📥 Mengunduh file ke server | ⏳ Harap tunggu... |\n"
            f"| 📦 Ukuran File | `{human_readable_size(film['file_size'])}` |\n"
            "| 🎬 Kualitas Stream | `720p HD Video + HQ Audio` |"
        )
        try:
            await RichParser.edit(
                query.message,
                loading_path_card,
                link_preview_options=LinkPreviewOptions(is_disabled=True),
            )
        except Exception:
            pass

        # Download file via userbot ke temp dir
        import os, asyncio
        from config import Config as Cfg
        os.makedirs(Cfg.TEMP_DIR, exist_ok=True)
        ext = os.path.splitext(film["file_name"])[-1] or ".mp4"
        local_path = os.path.join(Cfg.TEMP_DIR, f"film_{film['message_id']}{ext}")

        if not os.path.exists(local_path):
            try:
                import time as _time
                total_size = film.get("file_size") or 0
                last_update = [0.0]  # mutable for closure

                async def _progress(current: int, total: int):
                    nonlocal last_update
                    now = _time.time()
                    if now - last_update[0] < 3.5:
                        return
                    last_update[0] = now
                    pct = int(current / total * 100) if total else 0
                    filled = pct // 5
                    bar = "▓" * filled + "░" * (20 - filled)
                    dl_card = (
                        f"| 🎬 Mengunduh Film... |\n"
                        f"|:---:|\n"
                        f"| {clean_markdown(film['title'][:45])} |\n\n"
                        f"| Detail | Info |\n"
                        f"|:---|:---|\n"
                        f"| 📊 Progress | `[{bar}] {pct}%` |\n"
                        f"| 📥 Terunduh | `{human_readable_size(current)}` / `{human_readable_size(total)}` |\n"
                        f"| 📦 Total Size | `{human_readable_size(total_size)}` |\n"
                        f"| ⏳ Status | Harap tunggu sebentar... |"
                    )
                    try:
                        await RichParser.edit(
                            query.message,
                            dl_card,
                            link_preview_options=LinkPreviewOptions(is_disabled=True),
                        )
                    except Exception:
                        pass

                await userbot_client.download_media(
                    film["file_id"],
                    file_name=local_path,
                    progress=_progress,
                )
            except Exception as dl_err:
                logger.error(f"Gagal download film '{film['title']}': {dl_err}")
                await RichParser.edit(
                    query.message,
                    f"❌ Gagal mengunduh film: `{clean_markdown(str(dl_err))}`",
                )
                return

        track.file_path = local_path
        track.stream_url = local_path
        track.video_url = local_path

        # Putar via call_manager
        await call_manager.play_stream(chat.id, track)

        dur_str = get_readable_time(film.get("duration") or 0) if film.get("duration") else "Tidak Diketahui"
        size_str = human_readable_size(film.get("file_size") or 0)

        now_playing_card = (
            f"| 🎬 Sedang Memutar Film |\n"
            f"|:---:|\n"
            f"| |\n\n"
            f"| Parameter | Detail |\n"
            f"|:---|:---|\n"
            f"| 🎬 Judul Film | `{clean_markdown(film['title'][:60])}` |\n"
            f"| ⏱ Durasi | `{dur_str}` |\n"
            f"| 📦 Ukuran File | `{size_str}` |\n"
            f"| 👤 Diminta oleh | [{clean_markdown(user.first_name if user else 'Pengguna')}](tg://user?id={user.id if user else 0}) |\n"
            f"| 🎥 Format Stream | `Video HD 720p + Audio Stereo HQ` |\n\n"
            f"| 🤖 Nusantara Cinema 🎬 |\n"
            f"|:---:|\n"
            f"| |"
        )

        markup = get_control_panel(
            chat_id=chat.id,
            is_paused=False,
            is_looping=queue_manager.is_loop_enabled(chat.id),
            is_muted=queue_manager.is_muted(chat.id),
        )
        try:
            await RichParser.edit(
                query.message,
                now_playing_card,
                reply_markup=markup,
                link_preview_options=LinkPreviewOptions(is_disabled=True),
            )
        except Exception:
            pass

        queue_manager.set_now_playing_msg(chat.id, query.message.id)
        await send_stream_log(client, chat, track, is_video=True)

    except Exception as e:
        logger.error(f"Gagal memutar film '{film.get('title', '?')}': {e}")
        try:
            await RichParser.edit(
                query.message,
                f"❌ Gagal memutar film: `{clean_markdown(str(e))}`",
            )
        except Exception:
            await query.answer(f"❌ Gagal memutar film: {str(e)[:100]}", show_alert=True)


# ─────────────────────────────────────────────
#  CALLBACKS — TUTUP MENU
# ─────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^film_close$"))
async def film_close_callback(client: Client, query: CallbackQuery):
    """Menghapus/menutup pesan menu film."""
    try:
        await query.message.delete()
    except Exception:
        await query.answer("Pesan tidak dapat dihapus.", show_alert=False)


@Client.on_callback_query(filters.regex(r"^close_menu$"))
async def close_menu_callback(client: Client, query: CallbackQuery):
    """Handler universal tombol tutup/close untuk semua menu bot."""
    try:
        await query.message.delete()
    except Exception:
        await query.answer("Pesan tidak dapat dihapus.", show_alert=False)
