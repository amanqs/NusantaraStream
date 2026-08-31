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
    from kurigram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
    from kurigram.enums import ChatMemberStatus, ChatType
except ImportError:
    from pyrogram import Client, filters
    from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
    from pyrogram.enums import ChatMemberStatus, ChatType

from config import Config
from utils.database import db
from utils.queue import queue_manager
from utils.formatters import clean_markdown
from utils.keyboards import ButtonStyle
from utils.rich_parser import RichParser
from utils.decorators import BOT

logger = logging.getLogger("NusantaraStream.Settings")


def get_settings_keyboard(settings: dict) -> InlineKeyboardMarkup:
    """Membuat inline keyboard untuk panel pengaturan preferensi grup."""
    auth_mode = settings.get("auth_mode", "everyone")
    volume = settings.get("default_volume", 100)
    leave_time = settings.get("auto_leave_time", 300)
    autoplay = bool(settings.get("autoplay", 0))

    auth_label = "👥 Semua Member" if auth_mode == "everyone" else "🛡️ Hanya Admin"
    next_auth = "admin_only" if auth_mode == "everyone" else "everyone"
    ap_label = "🟢 Auto-Play: Aktif" if autoplay else "🔴 Auto-Play: Nonaktif"
    next_ap = 0 if autoplay else 1

    buttons = [
        # Baris 1: Mode Otorisasi Kontrol
        [
            InlineKeyboardButton(
                f"🔒 Kontrol: {auth_label}",
                callback_data=f"set_group_cfg:auth_mode:{next_auth}",
                style=ButtonStyle.SUCCESS if auth_mode == "everyone" else ButtonStyle.PRIMARY,
            )
        ],
        # Baris 2: Auto-Play Mode
        [
            InlineKeyboardButton(
                ap_label,
                callback_data=f"set_group_cfg:autoplay:{next_ap}",
                style=ButtonStyle.SUCCESS if autoplay else ButtonStyle.PRIMARY,
            )
        ],
        # Baris 3: Volume Bawaan
        [
            InlineKeyboardButton(
                "✅ 50%" if volume == 50 else "50%",
                callback_data="set_group_cfg:default_volume:50",
                style=ButtonStyle.SUCCESS if volume == 50 else ButtonStyle.PRIMARY,
            ),
            InlineKeyboardButton(
                "✅ 100%" if volume == 100 else "100%",
                callback_data="set_group_cfg:default_volume:100",
                style=ButtonStyle.SUCCESS if volume == 100 else ButtonStyle.PRIMARY,
            ),
            InlineKeyboardButton(
                "✅ 150%" if volume == 150 else "150%",
                callback_data="set_group_cfg:default_volume:150",
                style=ButtonStyle.SUCCESS if volume == 150 else ButtonStyle.PRIMARY,
            ),
        ],
        # Baris 4: Auto-Leave Timeout
        [
            InlineKeyboardButton(
                "✅ 3 Menit" if leave_time == 180 else "3 Menit",
                callback_data="set_group_cfg:auto_leave_time:180",
                style=ButtonStyle.SUCCESS if leave_time == 180 else ButtonStyle.PRIMARY,
            ),
            InlineKeyboardButton(
                "✅ 5 Menit" if leave_time == 300 else "5 Menit",
                callback_data="set_group_cfg:auto_leave_time:300",
                style=ButtonStyle.SUCCESS if leave_time == 300 else ButtonStyle.PRIMARY,
            ),
            InlineKeyboardButton(
                "✅ 10 Menit" if leave_time == 600 else "10 Menit",
                callback_data="set_group_cfg:auto_leave_time:600",
                style=ButtonStyle.SUCCESS if leave_time == 600 else ButtonStyle.PRIMARY,
            ),
        ],
        # Baris 5: Tutup Menu
        [
            InlineKeyboardButton(
                "🗑 Tutup Pengaturan",
                callback_data="help:close",
                style=ButtonStyle.DANGER,
            )
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def format_settings_card(settings: dict) -> str:
    """Format tampilan kartu pengaturan grup dalam format Telegram Rich Table Card."""
    auth_mode = settings.get("auth_mode", "everyone")
    volume = settings.get("default_volume", 100)
    leave_time = settings.get("auto_leave_time", 300)
    autoplay = bool(settings.get("autoplay", 0))

    auth_str = "👥 Semua Member (Bebas)" if auth_mode == "everyone" else "🛡️ Hanya Admin Grup"
    ap_str = "🟢 Aktif (Rekomendasi Otomatis)" if autoplay else "🔴 Nonaktif"
    leave_str = f"{leave_time // 60} Menit"

    card = (
        "| ⚙️ Panel Pengaturan Preferensi Grup |\n"
        "|:---:|\n"
        "| Sesuaikan konfigurasi pemutar musik grup Anda |\n\n"
        "| Opsi Konfigurasi | Status Aktif |\n"
        "|:---|:---|\n"
        f"| 🔒 Mode Kontrol | `{auth_str}` |\n"
        f"| 📻 Auto-Play Lagu | `{ap_str}` |\n"
        f"| 🔊 Volume Bawaan | `{volume}%` |\n"
        f"| ⏱ Auto-Leave VC | `{leave_str}` |\n\n"
        "| 💡 Klik tombol di bawah untuk mengubah preferensi: |\n"
        "|:---:|\n"
        "| |"
    )
    return card


@BOT("settings", "setting")
async def settings_command(client: Client, message: Message):
    """Handler perintah /settings untuk konfigurasi grup."""
    chat = message.chat
    sender = message.from_user

    if chat.type == ChatType.PRIVATE:
        return await RichParser.reply(
            message,
            "⚠️ *Fitur Pengaturan Grup hanya dapat digunakan di obrolan grup.*"
        )

    # Validasi admin grup / sudo
    if sender and sender.id not in Config.SUDO_USERS:
        member = await chat.get_member(sender.id)
        if member.status not in (
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR,
        ):
            return await RichParser.reply(
                message,
                "❌ *Hanya Admin Grup yang dapat mengubah pengaturan bot.*"
            )

    settings = await db.get_chat_settings(chat.id)
    card_text = format_settings_card(settings)
    markup = get_settings_keyboard(settings)

    await RichParser.reply(message, card_text, reply_markup=markup)


@BOT.on_callback_query(filters.regex(r"^set_group_cfg:(.+):(.+)"))
async def set_group_config_callback(client: Client, query: CallbackQuery):
    """Handler callback toggle pengaturan grup."""
    parts = query.data.split(":")
    key = parts[1]
    raw_val = parts[2]
    chat_id = query.message.chat.id
    sender = query.from_user

    # Validasi admin grup / sudo
    if sender and sender.id not in Config.SUDO_USERS:
        member = await query.message.chat.get_member(sender.id)
        if member.status not in (
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR,
        ):
            return await query.answer("❌ Hanya Admin Grup yang dapat mengubah preferensi.", show_alert=True)

    val = int(raw_val) if raw_val.isdigit() else raw_val
    await db.update_chat_setting(chat_id, key, val)
    if key == "autoplay":
        queue_manager.set_autoplay(chat_id, bool(val))

    settings = await db.get_chat_settings(chat_id)
    card_text = format_settings_card(settings)
    markup = get_settings_keyboard(settings)

    try:
        await RichParser.edit(query, card_text, reply_markup=markup)
    except Exception:
        pass
    await query.answer("✅ Pengaturan grup berhasil diperbarui!", show_alert=False)
