# ==============================================================================
#  🇮🇩 Nusantara Stream - Telegram Music & Video Streaming Bot
# ==============================================================================
#  Author   : Amang (@BukanDevelopers)
#  GitHub   : https://github.com/amanqs
#  Project  : Nusantara Stream Telegram Bot
#  License  : GNU General Public License v3.0
# ==============================================================================

import datetime
import logging
from typing import Optional

try:
    from kurigram import Client, filters
    from kurigram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
except ImportError:
    from pyrogram import Client, filters
    from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import Config
from utils.auto_backup import (
    is_autobackup_enabled,
    set_autobackup_enabled,
    get_autobackup_interval,
    set_autobackup_interval,
    get_last_backup_time,
    execute_and_send_backup,
)
from utils.formatters import clean_markdown
from utils.keyboards import ButtonStyle
from utils.rich_parser import RichParser

logger = logging.getLogger("NusantaraStream.AutoBackupPlugin")


def get_autobackup_panel_keyboard() -> InlineKeyboardMarkup:
    """Membuat keyboard kontrol konfigurasi auto-backup."""
    is_enabled = is_autobackup_enabled()
    curr_interval = get_autobackup_interval()

    toggle_text = "🔴 Matikan Auto-Backup" if is_enabled else "🟢 Aktifkan Auto-Backup"
    toggle_action = "off" if is_enabled else "on"
    toggle_style = ButtonStyle.DANGER if is_enabled else ButtonStyle.SUCCESS

    buttons = [
        [
            InlineKeyboardButton(
                toggle_text,
                callback_data=f"ab_cfg:toggle:{toggle_action}",
                style=toggle_style,
            )
        ],
        [
            InlineKeyboardButton(
                f"{'✅ ' if curr_interval == 6 else ''}6 Jam",
                callback_data="ab_cfg:interval:6",
                style=ButtonStyle.SUCCESS if curr_interval == 6 else ButtonStyle.PRIMARY,
            ),
            InlineKeyboardButton(
                f"{'✅ ' if curr_interval == 12 else ''}12 Jam",
                callback_data="ab_cfg:interval:12",
                style=ButtonStyle.SUCCESS if curr_interval == 12 else ButtonStyle.PRIMARY,
            ),
            InlineKeyboardButton(
                f"{'✅ ' if curr_interval == 24 else ''}24 Jam",
                callback_data="ab_cfg:interval:24",
                style=ButtonStyle.SUCCESS if curr_interval == 24 else ButtonStyle.PRIMARY,
            ),
        ],
        [
            InlineKeyboardButton(
                "🚀 Cadangkan Sekarang (Instant)",
                callback_data="ab_cfg:trigger_now:now",
                style=ButtonStyle.PRIMARY,
            )
        ],
        [
            InlineKeyboardButton(
                "🗑 Tutup Menu",
                callback_data="help:close",
                style=ButtonStyle.DANGER,
            )
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def format_autobackup_panel_card() -> str:
    """Format tampilan kartu pengaturan auto-backup."""
    is_enabled = is_autobackup_enabled()
    interval = get_autobackup_interval()
    last_time = get_last_backup_time()

    status_str = "🟢 AKTIF (Terjadwal)" if is_enabled else "🔴 NONAKTIF"
    last_str = (
        datetime.datetime.fromtimestamp(last_time).strftime("%Y-%m-%d %H:%M:%S")
        if last_time
        else "Belum ada riwayat"
    )

    targets = []
    if Config.LOG_GROUP_ID:
        targets.append(f"Grup Log (`{Config.LOG_GROUP_ID}`)")
    if Config.OWNER_ID:
        targets.append(f"Owner PM (`{Config.OWNER_ID}`)")
    target_str = ", ".join(targets) if targets else "⚠️ Belum dikonfigurasi (.env)"

    return (
        "| 🛡️ Panel Pengaturan Auto-Backup Database |\n"
        "|:---:|\n"
        "| Pencadangan otomatis database SQLite secara berkala |\n\n"
        "| Parameter Sistem | Nilai Konfigurasi |\n"
        "|:---|:---|\n"
        f"| 📡 Status Auto-Backup | `{status_str}` |\n"
        f"| ⏱ Interval Backup | Setiap `{interval}` Jam |\n"
        f"| 📬 Tujuan Pengiriman | {target_str} |\n"
        f"| 🕒 Terakhir Dicadangkan | `{last_str}` |\n\n"
        "| 💡 Berkas dikirim otomatis ke grup log atau pesan pribadi Owner |\n"
        "|:---:|\n"
        "| |"
    )


@Client.on_message(filters.command(["autobackup", "ab"]) & ~filters.forwarded)
async def autobackup_command_handler(client: Client, message: Message):
    """Handler perintah /autobackup untuk owner dan sudo."""
    user = message.from_user
    user_id = user.id if user else 0

    if not Config.is_sudo(user_id):
        return await RichParser.reply(
            message,
            "⚠️ *Perintah ini hanya dapat diakses oleh Owner Bot / Sudo Administrator.*",
        )

    args = message.command[1:] if len(message.command) > 1 else []

    if not args:
        card = format_autobackup_panel_card()
        markup = get_autobackup_panel_keyboard()
        return await RichParser.reply(message, card, reply_markup=markup)

    sub = args[0].lower()
    if sub in ("on", "enable", "aktif"):
        set_autobackup_enabled(True)
        card = format_autobackup_panel_card()
        markup = get_autobackup_panel_keyboard()
        return await RichParser.reply(message, card, reply_markup=markup)

    elif sub in ("off", "disable", "nonaktif"):
        set_autobackup_enabled(False)
        card = format_autobackup_panel_card()
        markup = get_autobackup_panel_keyboard()
        return await RichParser.reply(message, card, reply_markup=markup)

    elif sub in ("interval", "set"):
        if len(args) > 1 and args[1].isdigit():
            val = int(args[1])
            new_val = set_autobackup_interval(val)
            card = format_autobackup_panel_card()
            markup = get_autobackup_panel_keyboard()
            return await RichParser.reply(
                message,
                f"✅ **Interval auto-backup berhasil diatur menjadi `{new_val}` Jam.**\n\n" + card,
                reply_markup=markup,
            )
        else:
            return await RichParser.reply(
                message,
                "ℹ️ **Format Penggunaan:** `/autobackup interval <jumlah_jam>`\n"
                "> Contoh: `/autobackup interval 12`",
            )

    elif sub in ("now", "send", "trigger", "run"):
        status_msg = await RichParser.reply(message, "⏳ *Menjalankan pencadangan database instan...*")
        targets = [message.chat.id]
        if Config.LOG_GROUP_ID:
            targets.append(Config.LOG_GROUP_ID)

        success = await execute_and_send_backup(client, targets, is_auto=False)
        if success:
            try:
                await status_msg.delete()
            except Exception:
                pass
        else:
            await RichParser.edit(status_msg, "❌ **Gagal menjalankan backup database.**")
    else:
        card = format_autobackup_panel_card()
        markup = get_autobackup_panel_keyboard()
        return await RichParser.reply(message, card, reply_markup=markup)


@Client.on_callback_query(filters.regex(r"^ab_cfg:(toggle|interval|trigger_now):(.+)"))
async def autobackup_callback_handler(client: Client, query: CallbackQuery):
    """Handler callback inline keyboard konfigurasi auto-backup."""
    user = query.from_user
    user_id = user.id if user else 0

    if not Config.is_sudo(user_id):
        return await query.answer("⚠️ Hanya Owner / Sudo yang dapat mengubah konfigurasi ini!", show_alert=True)

    parts = query.data.split(":")
    action = parts[1]
    val = parts[2]

    if action == "toggle":
        new_state = (val == "on")
        set_autobackup_enabled(new_state)
        await query.answer(f"Auto-Backup {'diaktifkan 🟢' if new_state else 'dinonaktifkan 🔴'}")

    elif action == "interval":
        if val.isdigit():
            set_autobackup_interval(int(val))
            await query.answer(f"Interval diatur ke {val} Jam ⏱")

    elif action == "trigger_now":
        await query.answer("Memulai proses backup...")
        targets = [query.message.chat.id]
        if Config.LOG_GROUP_ID:
            targets.append(Config.LOG_GROUP_ID)
        await execute_and_send_backup(client, targets, is_auto=False)
        return

    card = format_autobackup_panel_card()
    markup = get_autobackup_panel_keyboard()

    try:
        await RichParser.edit(query, card, reply_markup=markup)
    except Exception:
        pass
