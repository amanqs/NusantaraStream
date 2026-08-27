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

logger = logging.getLogger("NusantaraStream.TV")

# Curated High-Reliability Indonesian & Global IPTV Streams
TV_CHANNELS = {
    # 🇮🇩 Berita & Nasional
    "tvri_nasional": {
        "name": "TVRI Nasional HD",
        "category": "nasional",
        "url": "https://tvri.my.id/live/nasional/index.m3u8",
        "fallback_url": "https://stream-01.tvri.go.id/live/eds/TVRI-Nasional/hls/TVRI-Nasional.m3u8",
        "thumb": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/TVRI_2019.svg/1200px-TVRI_2019.svg.png",
        "desc": "Saluran Televisi Publik Nasional Republik Indonesia",
    },
    "tvri_world": {
        "name": "TVRI World HD",
        "category": "nasional",
        "url": "https://stream-01.tvri.go.id/live/eds/TVRI-World/hls/TVRI-World.m3u8",
        "thumb": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/TVRI_2019.svg/1200px-TVRI_2019.svg.png",
        "desc": "Saluran Internasional Berita & Budaya Nusantara",
    },
    "kompas_tv": {
        "name": "Kompas TV HD",
        "category": "nasional",
        "url": "https://video.kompas.com/hls/live/kompastv.m3u8",
        "fallback_url": "https://live.kompas.tv/hls/kompastv.m3u8",
        "thumb": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Logo_Kompas_TV_2017.svg/1200px-Logo_Kompas_TV_2017.svg.png",
        "desc": "Berita Terkini & Terpercaya Indonesia",
    },
    "metro_tv": {
        "name": "Metro TV News",
        "category": "nasional",
        "url": "https://metro.medcom.id/live/live_metro.m3u8",
        "thumb": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f9/MetroTV_2010.svg/1200px-MetroTV_2010.svg.png",
        "desc": "Pelopor Televisi Berita 24 Jam Indonesia",
    },
    "sea_today": {
        "name": "SEA Today News",
        "category": "nasional",
        "url": "https://seatoday.useetv.com/live/seatoday.m3u8",
        "thumb": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/SEA_Today_logo.png/800px-SEA_Today_logo.png",
        "desc": "Southeast Asia English News Channel",
    },
    "berita_satu": {
        "name": "BTV (Berita Satu)",
        "category": "nasional",
        "url": "https://btv.useetv.com/live/btv.m3u8",
        "thumb": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/BTV_logo_2022.svg/1200px-BTV_logo_2022.svg.png",
        "desc": "Saluran Berita & Inspirasi Nasional",
    },
    # ⚽ Olahraga & Edukasi
    "tvri_sport": {
        "name": "TVRI Sport HD",
        "category": "sport",
        "url": "https://stream-01.tvri.go.id/live/eds/TVRI-Sport/hls/TVRI-Sport.m3u8",
        "thumb": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/TVRI_2019.svg/1200px-TVRI_2019.svg.png",
        "desc": "Siaran Olahraga Nasional & Internasional 24 Jam",
    },
    "tvri_edukasi": {
        "name": "TVRI Edukasi",
        "category": "sport",
        "url": "https://stream-01.tvri.go.id/live/eds/TVRI-Edukasi/hls/TVRI-Edukasi.m3u8",
        "thumb": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/TVRI_2019.svg/1200px-TVRI_2019.svg.png",
        "desc": "Saluran Pendidikan Anak & Pembelajaran Indonesia",
    },
    "redbull_tv": {
        "name": "Red Bull TV Live",
        "category": "sport",
        "url": "https://rbmn-live.akamaized.net/hls/live/590964/BoRB-AT/master.m3u8",
        "thumb": "https://resources.redbull.com/logos/redbulltv/v3/redbulltv-logo.png",
        "desc": "Extreme Sports, Action & Adventure Live",
    },
    # 🕌 Religi & Makkah Live
    "makkah_live": {
        "name": "Makkah Live 24/7",
        "category": "religi",
        "url": "https://win.holystream.live/live/makkahlive/playlist.m3u8",
        "thumb": "https://i.ytimg.com/vi/M6X_46_32pE/maxresdefault.jpg",
        "desc": "Siaran Langsung Masjidil Haram Makkah Al-Mukarramah",
    },
    "madinah_live": {
        "name": "Madinah Live 24/7",
        "category": "religi",
        "url": "https://win.holystream.live/live/madinahlive/playlist.m3u8",
        "thumb": "https://i.ytimg.com/vi/Q2tXk3h4b98/maxresdefault.jpg",
        "desc": "Siaran Langsung Masjid Nabawi Madinah Al-Munawwarah",
    },
    "rodja_tv": {
        "name": "Rodja TV",
        "category": "religi",
        "url": "https://live.rodja.tv/hls/rodjatv.m3u8",
        "thumb": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/Logo_Rodja_TV.png/800px-Logo_Rodja_TV.png",
        "desc": "Saluran Dakwah Islam & Kajian Sunnah",
    },
    # 🎶 Hiburan & Lofi
    "nusantara_tv": {
        "name": "Nusantara TV (NTV)",
        "category": "hiburan",
        "url": "https://nusantaratv.useetv.com/live/nusantaratv.m3u8",
        "thumb": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Nusantara_TV_logo.svg/1200px-Nusantara_TV_logo.svg.png",
        "desc": "Televisi Berita & Hiburan Nasional",
    },
    "lofi_live": {
        "name": "Lofi Girl 24/7 Stream",
        "category": "hiburan",
        "url": "https://playertest.longtailvideo.com/adaptive/oceans/oceans.m3u8",
        "thumb": "https://i.ytimg.com/vi/jfKfPfyJRdk/maxresdefault.jpg",
        "desc": "Lofi Beats to Relax / Study to 24 Jam",
    },
}

CATEGORIES = [
    ("nasional", "🇮🇩 Berita & Nasional"),
    ("sport", "⚽ Olahraga & Edukasi"),
    ("religi", "🕌 Religi & Makkah 24/7"),
    ("hiburan", "🎶 Hiburan & Live"),
]


def get_tv_keyboard(active_cat: str = "nasional") -> InlineKeyboardMarkup:
    """Membuat keyboard kategori dan tombol pilihan siaran TV interaktif."""
    keyboard = []

    # 1. Baris Kategori Tabs
    cat_buttons = []
    for cat_id, cat_title in CATEGORIES:
        style = ButtonStyle.SUCCESS if cat_id == active_cat else ButtonStyle.PRIMARY
        icon = "🔘" if cat_id == active_cat else "📁"
        cat_buttons.append(
            InlineKeyboardButton(
                f"{icon} {cat_title.split()[1]}",
                callback_data=f"tv_cat_{cat_id}",
                style=resolve_style(style),
            )
        )
    keyboard.append(cat_buttons[:2])
    keyboard.append(cat_buttons[2:])

    # 2. Tombol Channel untuk kategori aktif
    channel_buttons = []
    filtered = [
        (cid, cdata)
        for cid, cdata in TV_CHANNELS.items()
        if cdata["category"] == active_cat
    ]

    for cid, cdata in filtered:
        channel_buttons.append(
            [
                InlineKeyboardButton(
                    f"📺 {cdata['name']}",
                    callback_data=f"tv_play_{cid}",
                    style=resolve_style(ButtonStyle.DEFAULT),
                )
            ]
        )

    keyboard.extend(channel_buttons)

    # 3. Baris Navigasi Bawah
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


def format_tv_menu_card(active_cat: str = "nasional") -> str:
    """Format kartu tampilan menu Siaran TV interaktif."""
    cat_name = dict(CATEGORIES).get(active_cat, "Nasional")
    return (
        f"| 📺 Siaran Live TV & IPTV Indonesia 24/7 |\n"
        f"|:---:|\n"
        f"| Nonton bareng siaran televisi langsung di Voice Chat Video grup |\n\n"
        f"| Kategori Aktif | `{cat_name}` |\n"
        f"|:---|:---|\n"
        f"| 🎥 Kualitas Stream | `720p HD Video + HQ Audio` |\n"
        f"| ⚡ Mode Siaran | `24/7 Live IPTV Stream` |\n\n"
        f"| 💡 Pilih saluran TV di bawah untuk langsung menyiarkan ke Voice Chat: |\n"
        f"|:---:|\n"
        f"| |"
    )


@Client.on_message(filters.command(["tv", "iptv", "livetv"]) & ~filters.forwarded)
@bot_admin_check
async def tv_menu_command(client: Client, message: Message):
    """Handler perintah /tv untuk membuka menu Siaran Live TV Indonesia."""
    chat = message.chat

    # Custom direct URL stream: /tv https://...m3u8
    args = message.text.split(None, 1) if message.text else []
    if len(args) > 1:
        custom_url = args[1].strip()
        if custom_url.startswith("http://") or custom_url.startswith("https://"):
            user = message.from_user
            track = TrackInfo(
                title="Siaran Live IPTV Kustom",
                duration=0,
                stream_url=custom_url,
                video_url=custom_url,
                requester=user.first_name if user else "Pengguna",
                requester_id=user.id if user else 0,
                chat_id=chat.id,
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
                card_text = format_now_playing(track, is_paused=False)
                markup = get_control_panel(track)
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

    if chat.type == ChatType.PRIVATE:
        text = format_tv_menu_card("nasional")
        markup = get_tv_keyboard("nasional")
        return await RichParser.reply(
            message,
            text,
            reply_markup=markup,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )

    text = format_tv_menu_card("nasional")
    markup = get_tv_keyboard("nasional")
    await RichParser.reply(
        message,
        text,
        reply_markup=markup,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@Client.on_callback_query(filters.regex(r"^tv_cat_(\w+)"))
async def tv_category_callback(client: Client, query: CallbackQuery):
    """Callback navigasi antar-kategori saluran TV."""
    cat_id = query.matches[0].group(1)
    text = format_tv_menu_card(cat_id)
    markup = get_tv_keyboard(cat_id)

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


@Client.on_callback_query(filters.regex(r"^tv_play_(\w+)"))
async def tv_play_callback(client: Client, query: CallbackQuery):
    """Callback untuk langsung memutar saluran TV pilihan di Voice Chat Video."""
    channel_id = query.matches[0].group(1)
    cdata = TV_CHANNELS.get(channel_id)

    if not cdata:
        return await query.answer("❌ Saluran TV tidak ditemukan!", show_alert=True)

    chat = query.message.chat
    if chat.type == ChatType.PRIVATE:
        return await query.answer(
            "⚠️ Fitur ini hanya dapat digunakan di grup dengan Voice Chat aktif!",
            show_alert=True,
        )

    user = query.from_user
    track = TrackInfo(
        title=cdata["name"],
        duration=0,
        stream_url=cdata["url"],
        video_url=cdata["url"],
        thumbnail=cdata.get("thumb", ""),
        requester=user.first_name if user else "Pengguna",
        requester_id=user.id if user else 0,
        chat_id=chat.id,
        channel=cdata.get("desc", "Live TV Indonesia"),
        is_video=True,
        is_live=True,
    )

    await query.answer(f"📺 Memutar siaran {cdata['name']}...")

    try:
        await call_manager.play_stream(chat.id, track)
        card_text = format_now_playing(track, is_paused=False)
        markup = get_control_panel(track)

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
        logger.error(f"Gagal memutar siaran TV {cdata['name']}: {e}")
        await query.answer(f"❌ Gagal memutar saluran TV: {e}", show_alert=True)
