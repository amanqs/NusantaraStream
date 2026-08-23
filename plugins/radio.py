# ==============================================================================
#  🇮🇩 Nusantara Stream - Telegram Music & Video Streaming Bot
# ==============================================================================
#  Author   : Amang (@BukanDevelopers)
#  GitHub   : https://github.com/amanqs
#  Project  : Nusantara Stream Telegram Bot
#  License  : GNU General Public License v3.0
# ==============================================================================

import logging

try:
    from kurigram import Client, filters
    from kurigram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, LinkPreviewOptions
    from kurigram.enums import ChatType
except ImportError:
    from pyrogram import Client, filters
    from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, LinkPreviewOptions
    from pyrogram.enums import ChatType

from config import Config
from utils.call_manager import call_manager
from utils.queue import queue_manager, TrackInfo
from utils.formatters import clean_markdown, format_now_playing
from utils.keyboards import get_control_panel, resolve_style, ButtonStyle
from utils.rich_parser import RichParser
from utils.decorators import bot_admin_check
from utils.log_helper import send_stream_log

logger = logging.getLogger("NusantaraStream.Radio")

RADIO_STATIONS = [
    {
        "id": "prambors",
        "name": "Prambors FM Jakarta",
        "url": "https://masima.rastream.com/masima-pramborsjakarta",
        "freq": "102.2 FM",
        "city": "Jakarta",
    },
    {
        "id": "genfm",
        "name": "Gen FM 98.7 Jakarta",
        "url": "https://stream.rcs.revma.com/7qq79n95t8uvv",
        "freq": "98.7 FM",
        "city": "Jakarta",
    },
    {
        "id": "hardrock",
        "name": "Hard Rock FM",
        "url": "https://stream.rcs.revma.com/0z4z3q95t8uvv",
        "freq": "87.6 FM",
        "city": "Jakarta",
    },
    {
        "id": "iradio",
        "name": "I-Radio Jakarta",
        "url": "https://stream.rcs.revma.com/4q3k4k75t8uvv",
        "freq": "89.6 FM",
        "city": "Jakarta",
    },
    {
        "id": "traxfm",
        "name": "Trax FM",
        "url": "https://stream.rcs.revma.com/39660v95t8uvv",
        "freq": "101.4 FM",
        "city": "Jakarta",
    },
    {
        "id": "rodja",
        "name": "Radio Rodja 756 AM",
        "url": "https://live.radiorodja.com/;stream.mp3",
        "freq": "756 AM",
        "city": "Bogor",
    },
    {
        "id": "suarasby",
        "name": "Suara Surabaya FM",
        "url": "https://live.suarasurabaya.net/ssfm",
        "freq": "100.0 FM",
        "city": "Surabaya",
    },
    {
        "id": "deltafm",
        "name": "Delta FM Jakarta",
        "url": "https://masima.rastream.com/masima-deltajakarta",
        "freq": "99.1 FM",
        "city": "Jakarta",
    },
]


def get_radio_keyboard() -> InlineKeyboardMarkup:
    """Membuat inline keyboard daftar stasiun radio Indonesia."""
    buttons = []
    for i in range(0, len(RADIO_STATIONS), 2):
        row = []
        st1 = RADIO_STATIONS[i]
        row.append(
            InlineKeyboardButton(
                f"📻 {st1['name']}",
                callback_data=f"radio_play:{st1['id']}",
                style=ButtonStyle.PRIMARY,
            )
        )
        if i + 1 < len(RADIO_STATIONS):
            st2 = RADIO_STATIONS[i + 1]
            row.append(
                InlineKeyboardButton(
                    f"📻 {st2['name']}",
                    callback_data=f"radio_play:{st2['id']}",
                    style=ButtonStyle.PRIMARY,
                )
            )
        buttons.append(row)

    buttons.append(
        [
            InlineKeyboardButton(
                "🗑 Tutup Menu Radio",
                callback_data="help:close",
                style=ButtonStyle.DANGER,
            )
        ]
    )
    return InlineKeyboardMarkup(buttons)


@Client.on_message(filters.command(["radio", "live"]) & ~filters.forwarded)
@bot_admin_check
async def radio_menu_command(client: Client, message: Message):
    """Handler perintah /radio untuk memilih dan memutar radio siaran langsung 24/7."""
    chat = message.chat
    if chat.type == ChatType.PRIVATE:
        return await RichParser.reply(
            message,
            "⚠️ *Fitur Radio hanya dapat digunakan di obrolan grup atau Voice Chat.*"
        )

    card = (
        "| 📻 Stasiun Radio Indonesia 24/7 |\n"
        "|:---:|\n"
        "| Dengarkan siaran radio favorit langsung di Voice Chat |\n\n"
        "| No | Stasiun Radio | Frekuensi | Kota |\n"
        "|:---:|:---|:---:|:---:|\n"
    )

    for idx, st in enumerate(RADIO_STATIONS, start=1):
        card += f"| #{idx} | {st['name']} | `{st['freq']}` | {st['city']} |\n"

    card += (
        "\n| 💡 Pilih tombol stasiun radio di bawah untuk memutar: |\n"
        "|:---:|\n"
        "| |"
    )

    markup = get_radio_keyboard()
    await RichParser.reply(message, card, reply_markup=markup)


@Client.on_callback_query(filters.regex(r"^radio_play:(.+)"))
async def radio_play_callback(client: Client, query: CallbackQuery):
    """Handler callback tombol radio untuk langsung memutar siaran di Voice Chat."""
    station_id = query.data.split(":")[1]
    chat_id = query.message.chat.id
    user = query.from_user
    user_name = clean_markdown(user.first_name if user else "Pengguna")

    selected = next((s for s in RADIO_STATIONS if s["id"] == station_id), None)
    if not selected:
        return await query.answer("Stasiun radio tidak ditemukan.", show_alert=True)

    await query.answer(f"Memulai siaran {selected['name']}...")

    track = TrackInfo(
        title=f"Radio: {selected['name']}",
        url=selected["url"],
        stream_url=selected["url"],
        duration=0,
        channel=f"{selected['name']} ({selected['freq']})",
        requested_by_id=user.id if user else 0,
        requested_by_name=user_name,
        is_video=False,
        is_live=True,
    )

    # Putar langsung di Voice Chat
    try:
        await call_manager.play_stream(chat_id, track)
        queue_manager.clear_queue(chat_id)
        queue_manager.set_current_track(chat_id, track)

        card_text = format_now_playing(
            track=track,
            current_sec=0,
            is_paused=False,
            is_looping=False,
            volume=queue_manager.get_volume(chat_id),
            is_muted=queue_manager.is_muted(chat_id),
        )
        markup = get_control_panel(
            chat_id=chat_id,
            is_paused=False,
            is_looping=False,
            is_muted=queue_manager.is_muted(chat_id),
        )
        await RichParser.edit(
            query,
            card_text,
            reply_markup=markup,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )

        # Kirim log streaming radio ke LOG_GROUP_ID
        await send_stream_log(
            client,
            chat_id,
            query.message.chat.title or "Voice Chat",
            track,
            is_radio=True,
        )
    except Exception as e:
        logger.error(f"Gagal memutar radio: {e}")
        await RichParser.edit(
            query,
            f"❌ **Gagal memutar siaran radio:** `{clean_markdown(str(e))}`"
        )


# Alias untuk kompatibilitas impor
radio_command = radio_menu_command
