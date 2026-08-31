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
    from kurigram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
    from kurigram.enums import ChatMemberStatus
except ImportError:
    from pyrogram import Client, filters
    from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
    from pyrogram.enums import ChatMemberStatus

from config import Config
from utils.database import db
from utils.queue import queue_manager
from utils.formatters import clean_markdown
from utils.rich_parser import RichParser
from utils.decorators import BOT

logger = logging.getLogger("NusantaraStream.AutoPlay")


def get_autoplay_keyboard(is_enabled: bool) -> InlineKeyboardMarkup:
    """Membuat keyboard toggle Auto-Play interaktif."""
    if is_enabled:
        btn_text = "🔴 Matikan Auto-Play"
        action = "off"
    else:
        btn_text = "🟢 Aktifkan Auto-Play"
        action = "on"

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(btn_text, callback_data=f"ap:{action}"),
            ],
            [
                InlineKeyboardButton("🗑 Tutup Menu", callback_data="help:close"),
            ],
        ]
    )


def format_autoplay_card(is_enabled: bool, changed_by: str = "") -> str:
    """Membuat kartu Table Card status mode Auto-Play."""
    status_badge = "🟢 AKTIF (ON)" if is_enabled else "🔴 NONAKTIF (OFF)"
    desc = (
        "Lagu rekomendasi serupa akan diputar otomatis tanpa henti saat antrean habis."
        if is_enabled
        else "Bot akan otomatis meninggalkan Voice Chat saat seluruh lagu antrean selesai."
    )

    admin_row = f"\n| 🛡 Diatur Oleh | {changed_by} |" if changed_by else ""

    return (
        "| 📻 Pengaturan Mode Auto-Play Grup |\n"
        "|:---:|\n"
        "| Sistem rekomendasi lagu cerdas tanpa jeda |\n\n"
        "| Parameter | Nilai Status |\n"
        "|:---|:---|\n"
        f"| 📡 Status Auto-Play | `{status_badge}` |\n"
        f"| 🎵 Perilaku Sistem | {desc} |{admin_row}\n\n"
        "| 💡 Klik tombol di bawah atau ketik `/autoplay on|off` |\n"
        "|:---:|\n"
        "| |"
    )


async def _is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    """Cek apakah user adalah admin grup atau sudo."""
    if Config.is_sudo(user_id):
        return True
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR)
    except Exception:
        return False


@BOT("autoplay", "ap")
async def autoplay_command(client: Client, message: Message):
    """Handler perintah /autoplay untuk mengaktifkan / menonaktifkan lagu rekomendasi otomatis."""
    chat = message.chat
    user = message.from_user

    if chat.type.value not in ("group", "supergroup"):
        return await RichParser.reply(
            message,
            "ℹ️ *Perintah Auto-Play hanya dapat digunakan di dalam obrolan grup.*",
        )

    # Verifikasi hak akses admin
    if user and not await _is_admin(client, chat.id, user.id):
        return await RichParser.reply(
            message,
            "⚠️ *Anda harus menjadi Admin Grup untuk mengubah pengaturan Auto-Play.*",
        )

    cmd_args = message.command[1:] if len(message.command) > 1 else []
    curr_status = await db.get_autoplay(chat.id)
    # Sinkronisasi ke runtime memory jika belum
    queue_manager.set_autoplay(chat.id, curr_status)

    user_name = clean_markdown(user.first_name if user else "Admin").replace("|", "\\|")

    if not cmd_args:
        # Tampilkan status & keyboard toggle
        card = format_autoplay_card(curr_status)
        markup = get_autoplay_keyboard(curr_status)
        return await RichParser.reply(message, card, reply_markup=markup)

    arg = cmd_args[0].lower()
    if arg in ("on", "enable", "aktif", "1", "true"):
        new_state = True
    elif arg in ("off", "disable", "nonaktif", "0", "false"):
        new_state = False
    elif arg in ("toggle", "switch"):
        new_state = not curr_status
    elif arg in ("status", "info"):
        card = format_autoplay_card(curr_status)
        markup = get_autoplay_keyboard(curr_status)
        return await RichParser.reply(message, card, reply_markup=markup)
    else:
        return await RichParser.reply(
            message,
            "ℹ️ **Format Perintah Auto-Play:**\n"
            "> - `/autoplay on` : Mengaktifkan pemutaran rekomendasi otomatis\n"
            "> - `/autoplay off` : Menonaktifkan mode Auto-Play\n"
            "> - `/autoplay` : Tampilkan panel tombol kontrol status",
        )

    # Simpan ke database dan queue manager
    await db.set_autoplay(chat.id, new_state)
    queue_manager.set_autoplay(chat.id, new_state)

    card = format_autoplay_card(new_state, changed_by=user_name)
    markup = get_autoplay_keyboard(new_state)
    await RichParser.reply(message, card, reply_markup=markup)


@BOT.on_callback_query(filters.regex(r"^ap:(on|off|toggle)"))
async def autoplay_callback_handler(client: Client, query: CallbackQuery):
    """Handler callback inline button toggle Auto-Play."""
    chat = query.message.chat
    user = query.from_user

    if not await _is_admin(client, chat.id, user.id):
        return await query.answer("⚠️ Hanya admin grup yang dapat mengubah Auto-Play!", show_alert=True)

    action = query.data.split(":")[1]
    curr_status = await db.get_autoplay(chat.id)

    if action == "on":
        new_state = True
    elif action == "off":
        new_state = False
    else:
        new_state = not curr_status

    await db.set_autoplay(chat.id, new_state)
    queue_manager.set_autoplay(chat.id, new_state)

    user_name = clean_markdown(user.first_name if user else "Admin").replace("|", "\\|")
    card = format_autoplay_card(new_state, changed_by=user_name)
    markup = get_autoplay_keyboard(new_state)

    try:
        await RichParser.edit(query, card, reply_markup=markup)
    except Exception:
        pass

    state_text = "diaktifkan 🟢" if new_state else "dinonaktifkan 🔴"
    await query.answer(f"Mode Auto-Play berhasil {state_text}.")
