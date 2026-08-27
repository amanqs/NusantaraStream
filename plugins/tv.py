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
    from kurigram.types import (
        Message,
        InlineKeyboardMarkup,
        InlineKeyboardButton,
        CallbackQuery,
        LinkPreviewOptions,
    )
    from kurigram.enums import ChatType
except ImportError:
    from pyrogram import Client, filters
    from pyrogram.types import (
        Message,
        InlineKeyboardMarkup,
        InlineKeyboardButton,
        CallbackQuery,
        LinkPreviewOptions,
    )
    from pyrogram.enums import ChatType

from config import Config
from utils.call_manager import call_manager
from utils.queue import queue_manager, TrackInfo
from utils.formatters import clean_markdown, format_now_playing
from utils.keyboards import get_control_panel, resolve_style, ButtonStyle
from utils.rich_parser import RichParser
from utils.decorators import bot_admin_check
from utils.log_helper import send_stream_log
from utils.iptv_manager import iptv_manager, IPTV_SOURCES

logger = logging.getLogger("NusantaraStream.TV")

# Kategori IPTV
TV_CATEGORIES = [
    ("indonesia", "🇮🇩 Indonesia"),
    ("news", "📰 Berita Global"),
    ("sports", "⚽ Olahraga"),
    ("religious", "🕌 Religi & Makkah"),
    ("music", "🎶 Musik Live"),
    ("kids", "🧸 Anak & Kartun"),
]

# Cache sementara hasil pencarian: search_id -> list[dict]
SEARCH_CHANNEL_CACHE: dict[str, list[dict]] = {}
CHANNELS_PER_PAGE = 5


def get_tv_browser_keyboard(category: str, channels: list[dict], page: int = 1) -> InlineKeyboardMarkup:
    """Membuat keyboard penjelajah saluran TV berhalaman dari iptv-org."""
    keyboard = []

    # 1. Baris Kategori Tabs (2 baris x 3 kolom)
    row1 = []
    row2 = []
    for i, (cat_id, cat_title) in enumerate(TV_CATEGORIES):
        style = ButtonStyle.SUCCESS if cat_id == category else ButtonStyle.PRIMARY
        icon = "🔘" if cat_id == category else "📁"
        btn = InlineKeyboardButton(
            f"{icon} {cat_title.split()[1]}",
            callback_data=f"tv_cat:{cat_id}:1",
            style=resolve_style(style),
        )
        if i < 3:
            row1.append(btn)
        else:
            row2.append(btn)
    keyboard.append(row1)
    keyboard.append(row2)

    # 2. Tombol Channel untuk halaman aktif
    total_channels = len(channels)
    total_pages = max(1, (total_channels + CHANNELS_PER_PAGE - 1) // CHANNELS_PER_PAGE)
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * CHANNELS_PER_PAGE
    end_idx = start_idx + CHANNELS_PER_PAGE
    current_page_channels = channels[start_idx:end_idx]

    for idx_in_page, ch in enumerate(current_page_channels):
        real_idx = start_idx + idx_in_page
        ch_name = clean_markdown(ch["title"])[:30]
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"📺 {ch_name}",
                    callback_data=f"tv_p:{category}:{real_idx}",
                    style=resolve_style(ButtonStyle.DEFAULT),
                )
            ]
        )

    # 3. Baris Navigasi Halaman
    nav_row = []
    if page > 1:
        nav_row.append(
            InlineKeyboardButton(
                "⬅️ Prev",
                callback_data=f"tv_cat:{category}:{page - 1}",
                style=resolve_style(ButtonStyle.PRIMARY),
            )
        )
    nav_row.append(
        InlineKeyboardButton(
            f"📄 {page}/{total_pages}",
            callback_data="tv_page_info",
            style=resolve_style(ButtonStyle.DEFAULT),
        )
    )
    if page < total_pages:
        nav_row.append(
            InlineKeyboardButton(
                "Next ➡️",
                callback_data=f"tv_cat:{category}:{page + 1}",
                style=resolve_style(ButtonStyle.PRIMARY),
            )
        )
    keyboard.append(nav_row)

    # 4. Baris Tutup Menu
    keyboard.append(
        [
            InlineKeyboardButton(
                "❌ Tutup Menu",
                callback_data="close_menu",
                style=resolve_style(ButtonStyle.DANGER),
            )
        ]
    )

    return InlineKeyboardMarkup(keyboard)


def format_tv_menu_card(category: str, total_channels: int, page: int = 1) -> str:
    """Format kartu tampilan menu Siaran TV interaktif iptv-org."""
    cat_name = dict(TV_CATEGORIES).get(category, "Indonesia")
    total_pages = max(1, (total_channels + CHANNELS_PER_PAGE - 1) // CHANNELS_PER_PAGE)

    return (
        f"| 📺 Siaran Live TV & IPTV Indonesia 24/7 |\n"
        f"|:---:|\n"
        f"| Nonton bareng siaran TV langsung di Voice Chat Video grup |\n\n"
        f"| Kategori Aktif | `{cat_name}` |\n"
        f"|:---|:---|\n"
        f"| 📡 Total Saluran | `{total_channels}` Saluran Aktif |\n"
        f"| 📄 Halaman | `{page} / {total_pages}` |\n"
        f"| 🎥 Kualitas Stream | `720p HD Video + HQ Audio` |\n"
        f"| 🌐 Sumber Data | `IPTV-Org Live Open Stream` |\n\n"
        f"| 💡 Klik nama saluran TV di bawah untuk langsung menyiarkan ke Voice Chat: |\n"
        f"|:---:|\n"
        f"| |"
    )


@Client.on_message(filters.command(["tv", "iptv", "livetv"]) & ~filters.forwarded)
@bot_admin_check
async def tv_menu_command(client: Client, message: Message):
    """Handler perintah /tv untuk membuka menu Siaran Live TV atau mencari saluran."""
    chat = message.chat
    args = message.text.split(None, 1) if message.text else []

    # 1. Kasus jika query adalah URL langsung: /tv https://...m3u8
    if len(args) > 1:
        query = args[1].strip()
        if query.startswith("http://") or query.startswith("https://"):
            user = message.from_user
            track = TrackInfo(
                title="Siaran Live IPTV Kustom",
                url=query,
                stream_url=query,
                duration=0,
                video_url=query,
                requested_by_name=user.first_name if user else "Pengguna",
                requested_by_id=user.id if user else 0,
                channel="IPTV Custom Stream",
                is_video=True,
                is_live=True,
            )

            status_msg = await RichParser.reply(
                message,
                "| 📡 Menghubungkan Siaran IPTV... |\n|:---:|\n| Membuka stream video 720p HD di Voice Chat |",
            )

            try:
                await call_manager.play_stream(chat.id, track)
                card_text = format_now_playing(
                    track=track,
                    current_sec=0,
                    is_paused=False,
                    is_looping=queue_manager.is_loop_enabled(chat.id),
                    volume=queue_manager.get_volume(chat.id),
                    is_muted=queue_manager.is_muted(chat.id),
                )
                markup = get_control_panel(
                    chat_id=chat.id,
                    is_paused=False,
                    is_looping=queue_manager.is_loop_enabled(chat.id),
                    is_muted=queue_manager.is_muted(chat.id),
                )
                await RichParser.reply(
                    message,
                    card_text,
                    reply_markup=markup,
                    link_preview_options=LinkPreviewOptions(is_disabled=True),
                )
                try:
                    await status_msg.delete()
                except Exception:
                    pass
                await send_stream_log(client, chat, track, is_video=True)
                return
            except Exception as e:
                logger.error(f"Gagal memutar custom IPTV: {e}")
                return await RichParser.reply(
                    message, f"❌ Gagal memutar URL IPTV: `{clean_markdown(str(e))}`"
                )

        # 2. Kasus jika query adalah kata kunci pencarian nama TV: /tv antv / /tv kompas
        search_status = await RichParser.reply(
            message,
            f"🔍 *Mencari saluran siaran TV untuk:* `{clean_markdown(query)}`...",
        )
        results = await iptv_manager.search_channel(query)
        if not results:
            return await RichParser.edit(
                search_status,
                f"❌ Tidak ditemukan saluran TV dengan kata kunci `{clean_markdown(query)}`.\n"
                f"Ketik `/tv` untuk melihat daftar lengkap saluran TV Indonesia.",
            )

        # Jika hanya ada 1 saluran yang cocok, langsung putar
        if len(results) == 1:
            ch = results[0]
            user = message.from_user
            track = TrackInfo(
                title=ch["title"],
                url=ch["url"],
                stream_url=ch["url"],
                duration=0,
                video_url=ch["url"],
                thumbnail=ch.get("logo", ""),
                requested_by_name=user.first_name if user else "Pengguna",
                requested_by_id=user.id if user else 0,
                channel=f"IPTV • {ch.get('group', 'Indonesia')}",
                is_video=True,
                is_live=True,
            )
            try:
                await call_manager.play_stream(chat.id, track)
                card_text = format_now_playing(
                    track=track,
                    current_sec=0,
                    is_paused=False,
                    is_looping=queue_manager.is_loop_enabled(chat.id),
                    volume=queue_manager.get_volume(chat.id),
                    is_muted=queue_manager.is_muted(chat.id),
                )
                markup = get_control_panel(
                    chat_id=chat.id,
                    is_paused=False,
                    is_looping=queue_manager.is_loop_enabled(chat.id),
                    is_muted=queue_manager.is_muted(chat.id),
                )
                await RichParser.reply(
                    message,
                    card_text,
                    reply_markup=markup,
                    link_preview_options=LinkPreviewOptions(is_disabled=True),
                )
                try:
                    await search_status.delete()
                except Exception:
                    pass
                await send_stream_log(client, chat, track, is_video=True)
                return
            except Exception as e:
                logger.error(f"Gagal memutar siaran TV: {e}")
                return await RichParser.edit(search_status, f"❌ Gagal memutar saluran TV: `{e}`")

        # Jika ada beberapa pilihan, tampilkan tombol pilihan
        search_key = f"{chat.id}_{message.id}"
        SEARCH_CHANNEL_CACHE[search_key] = results

        buttons = []
        for i, ch in enumerate(results[:6]):
            buttons.append(
                [
                    InlineKeyboardButton(
                        f"📺 {ch['title'][:32]}",
                        callback_data=f"tv_splay:{search_key}:{i}",
                        style=resolve_style(ButtonStyle.DEFAULT),
                    )
                ]
            )
        buttons.append(
            [
                InlineKeyboardButton(
                    "❌ Tutup",
                    callback_data="close_menu",
                    style=resolve_style(ButtonStyle.DANGER),
                )
            ]
        )

        card_search = (
            f"| 📺 Hasil Pencarian Saluran TV |\n"
            f"|:---:|\n"
            f"| Ditemukan `{len(results)}` saluran untuk kata kunci `{clean_markdown(query)}` |\n\n"
            f"| 💡 Pilih saluran di bawah untuk langsung menyiarkan ke Voice Chat: |\n"
            f"|:---:|\n"
            f"| |"
        )
        return await RichParser.edit(
            search_status,
            card_search,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    # 3. Tampilkan Menu Browser Saluran TV Kategori
    loading_msg = await RichParser.reply(message, "⏳ *Memuat daftar saluran TV dari IPTV-Org...*")
    channels = await iptv_manager.fetch_channels("indonesia")
    text = format_tv_menu_card("indonesia", len(channels), page=1)
    markup = get_tv_browser_keyboard("indonesia", channels, page=1)

    await RichParser.reply(
        message,
        text,
        reply_markup=markup,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    try:
        await loading_msg.delete()
    except Exception:
        pass


@Client.on_callback_query(filters.regex(r"^tv_cat:(\w+):(\d+)"))
async def tv_category_nav_callback(client: Client, query: CallbackQuery):
    """Callback navigasi antar-kategori dan pagination halaman saluran TV."""
    category = query.matches[0].group(1)
    page = int(query.matches[0].group(2))

    channels = await iptv_manager.fetch_channels(category)
    text = format_tv_menu_card(category, len(channels), page=page)
    markup = get_tv_browser_keyboard(category, channels, page=page)

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


@Client.on_callback_query(filters.regex(r"^tv_p:(\w+):(\d+)"))
async def tv_channel_play_callback(client: Client, query: CallbackQuery):
    """Callback untuk langsung memutar saluran TV pilihan di Voice Chat Video."""
    category = query.matches[0].group(1)
    channel_idx = int(query.matches[0].group(2))

    channels = await iptv_manager.fetch_channels(category)
    if channel_idx >= len(channels):
        return await query.answer("❌ Saluran TV tidak ditemukan atau kadaluarsa.", show_alert=True)

    ch = channels[channel_idx]
    chat = query.message.chat

    if chat.type == ChatType.PRIVATE:
        return await query.answer(
            "⚠️ Fitur ini hanya dapat digunakan di grup dengan Voice Chat aktif!",
            show_alert=True,
        )

    user = query.from_user
    track = TrackInfo(
        title=ch["title"],
        url=ch["url"],
        stream_url=ch["url"],
        duration=0,
        video_url=ch["url"],
        thumbnail=ch.get("logo", ""),
        requested_by_name=user.first_name if user else "Pengguna",
        requested_by_id=user.id if user else 0,
        channel=f"IPTV • {ch.get('group', 'Indonesia')}",
        is_video=True,
        is_live=True,
    )

    await query.answer(f"📺 Menyiarkan {ch['title'][:25]}...")

    try:
        await call_manager.play_stream(chat.id, track)
        card_text = format_now_playing(
            track=track,
            current_sec=0,
            is_paused=False,
            is_looping=queue_manager.is_loop_enabled(chat.id),
            volume=queue_manager.get_volume(chat.id),
            is_muted=queue_manager.is_muted(chat.id),
        )
        markup = get_control_panel(
            chat_id=chat.id,
            is_paused=False,
            is_looping=queue_manager.is_loop_enabled(chat.id),
            is_muted=queue_manager.is_muted(chat.id),
        )

        await RichParser.reply(
            query.message,
            card_text,
            reply_markup=markup,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )

        try:
            await query.message.delete()
        except Exception:
            pass

        await send_stream_log(client, chat, track, is_video=True)
    except Exception as e:
        logger.error(f"Gagal memutar siaran TV {ch['title']}: {e}")
        await query.answer(f"❌ Gagal memutar saluran TV: {e}", show_alert=True)


@Client.on_callback_query(filters.regex(r"^tv_splay:([^:]+):(\d+)"))
async def tv_search_play_callback(client: Client, query: CallbackQuery):
    """Callback untuk memutar hasil pencarian siaran TV."""
    search_key = query.matches[0].group(1)
    ch_idx = int(query.matches[0].group(2))

    results = SEARCH_CHANNEL_CACHE.get(search_key)
    if not results or ch_idx >= len(results):
        return await query.answer("❌ Hasil pencarian telah kadaluarsa. Cari ulang dengan /tv <nama>", show_alert=True)

    ch = results[ch_idx]
    chat = query.message.chat

    if chat.type == ChatType.PRIVATE:
        return await query.answer(
            "⚠️ Fitur ini hanya dapat digunakan di grup dengan Voice Chat aktif!",
            show_alert=True,
        )

    user = query.from_user
    track = TrackInfo(
        title=ch["title"],
        url=ch["url"],
        stream_url=ch["url"],
        duration=0,
        video_url=ch["url"],
        thumbnail=ch.get("logo", ""),
        requested_by_name=user.first_name if user else "Pengguna",
        requested_by_id=user.id if user else 0,
        channel=f"IPTV • {ch.get('group', 'Indonesia')}",
        is_video=True,
        is_live=True,
    )

    await query.answer(f"📺 Menyiarkan {ch['title'][:25]}...")

    try:
        await call_manager.play_stream(chat.id, track)
        card_text = format_now_playing(
            track=track,
            current_sec=0,
            is_paused=False,
            is_looping=queue_manager.is_loop_enabled(chat.id),
            volume=queue_manager.get_volume(chat.id),
            is_muted=queue_manager.is_muted(chat.id),
        )
        markup = get_control_panel(
            chat_id=chat.id,
            is_paused=False,
            is_looping=queue_manager.is_loop_enabled(chat.id),
            is_muted=queue_manager.is_muted(chat.id),
        )

        await RichParser.reply(
            query.message,
            card_text,
            reply_markup=markup,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )

        try:
            await query.message.delete()
        except Exception:
            pass

        await send_stream_log(client, chat, track, is_video=True)
    except Exception as e:
        logger.error(f"Gagal memutar siaran TV {ch['title']}: {e}")
        await query.answer(f"❌ Gagal memutar saluran TV: {e}", show_alert=True)


@Client.on_callback_query(filters.regex(r"^tv_page_info$"))
async def tv_page_info_callback(client: Client, query: CallbackQuery):
    """Informasi halaman saluran TV saat tombol halaman diklik."""
    await query.answer("ℹ️ Gunakan tombol Prev / Next untuk berpindah halaman saluran TV.", show_alert=False)
