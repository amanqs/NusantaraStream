# ==============================================================================
#  🇮🇩 Nusantara Stream - Telegram Music & Video Streaming Bot
# ==============================================================================
#  Author   : Amang (@BukanDevelopers)
#  GitHub   : https://github.com/amanqs
#  Project  : Nusantara Stream Telegram Bot
#  License  : GNU General Public License v3.0
# ==============================================================================

import asyncio
import time
import logging

try:
    from kurigram import Client, filters
    from kurigram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
    from kurigram.enums import ChatMemberStatus, ChatType
    from kurigram.errors import (
        FloodWait,
        UserIsBlocked,
        InputUserDeactivated,
        PeerIdInvalid,
        ChatAdminRequired,
        ChatWriteForbidden,
        ChannelPrivate,
        UserAdminInvalid,
    )
except ImportError:
    from pyrogram import Client, filters
    from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
    from pyrogram.enums import ChatMemberStatus, ChatType
    try:
        from pyrogram.errors import (
            FloodWait,
            UserIsBlocked,
            InputUserDeactivated,
            PeerIdInvalid,
            ChatAdminRequired,
            ChatWriteForbidden,
            ChannelPrivate,
            UserAdminInvalid,
        )
    except ImportError:
        class FloodWait(Exception):
            value = 0
        class UserIsBlocked(Exception): pass
        class InputUserDeactivated(Exception): pass
        class PeerIdInvalid(Exception): pass
        class ChatAdminRequired(Exception): pass
        class ChatWriteForbidden(Exception): pass
        class ChannelPrivate(Exception): pass
        class UserAdminInvalid(Exception): pass

from config import Config
from utils.database import db
from utils.formatters import clean_markdown
from utils.rich_parser import RichParser
from utils.decorators import BOT, USER

logger = logging.getLogger("NusantaraStream.GBan")


@BOT("gban", "globalban")
async def gban_command(client: Client, message: Message):
    """[Sudo/Owner] Melarang (Global Ban) pengguna secara massal di seluruh grup bot."""
    sender = message.from_user
    if not sender or not Config.is_sudo(sender.id):
        return await RichParser.reply(
            message,
            "❌ *Perintah ini hanya dapat digunakan oleh Sudo Admin atau Pemilik Bot.*"
        )

    target_user = None
    reason = "Tidak ada alasan spesifik."

    # 1. Cek jika mereply ke pesan user
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        if len(message.command) > 1:
            reason = " ".join(message.command[1:])
    # 2. Cek jika menyertakan parameter username atau user_id
    elif len(message.command) > 1:
        user_input = message.command[1]
        if user_input.isdigit():
            user_input = int(user_input)
        try:
            target_user = await client.get_users(user_input)
        except Exception:
            return await RichParser.reply(message, "❌ *Pengguna tidak ditemukan atau ID tidak valid.*")

        if len(message.command) > 2:
            reason = " ".join(message.command[2:])

    # 3. Validasi target_user
    if not target_user:
        guide_card = (
            "| ℹ️ Panduan Perintah Global Ban (GBan) |\n"
            "|:---:|\n"
            "| Melarang pengguna secara massal di seluruh grup bot |\n\n"
            "| Format Perintah | Keterangan |\n"
            "|:---|:---|\n"
            "| `/gban [alasan]` (balas pesan) | GBan pengguna yang dibalas |\n"
            "| `/gban @username [alasan]` | GBan via username Telegram |\n"
            "| `/gban [user_id] [alasan]` | GBan via User ID |\n\n"
            "| 🤖 Nusantara Stream 🤖 |\n"
            "|:---:|\n"
            "| |"
        )
        return await RichParser.reply(message, guide_card)

    # 4. Pengecekan Kekebalan (Immunity Checks)
    bot_id = getattr(client, "id", 0) or (client.me.id if getattr(client, "me", None) else 0)
    if target_user.id == bot_id:
        return await RichParser.reply(message, "❌ *Tidak dapat melakukan Global Ban terhadap akun bot ini sendiri.*")

    if Config.is_developer(target_user.id) or target_user.id in Config.DEVELOPER_IDS:
        return await RichParser.reply(message, "❌ *Tidak dapat melakukan Global Ban terhadap Developer / Pembuat Asli bot!*")

    if target_user.id == Config.OWNER_ID:
        return await RichParser.reply(message, "❌ *Tidak dapat melakukan Global Ban terhadap Pemilik (Owner) bot!*")

    if target_user.id in Config.SUDO_USERS:
        return await RichParser.reply(
            message,
            "❌ *Pengguna ini adalah Sudo Admin.*\n"
            "> Silakan cabut hak akses sudo terlebih dahulu dengan `/delsudo` sebelum melakukan GBan."
        )

    # 5. Cek apakah pengguna sudah di-GBan
    if db.is_user_gbanned(target_user.id):
        existing = await db.get_gban_user(target_user.id)
        ex_reason = existing.get("reason", "-") if existing else "-"
        ex_date = existing.get("banned_date", "-") if existing else "-"
        return await RichParser.reply(
            message,
            f"ℹ️ {target_user.mention} *sudah terdaftar dalam Global Ban.*\n"
            f"> **Alasan:** `{clean_markdown(ex_reason)}`\n"
            f"> **Tanggal:** `{ex_date}`"
        )

    # 6. Simpan ke database
    banner_name = sender.first_name or f"User {sender.id}"
    t_name = target_user.first_name or ""
    t_uname = target_user.username or ""
    await db.add_gban_user(
        user_id=target_user.id,
        first_name=t_name,
        username=t_uname,
        reason=reason,
        banned_by=sender.id,
        banned_by_name=banner_name,
    )

    # 7. Eksekusi ban di seluruh grup terlayani
    served_chats = await db.get_served_chats()
    total_chats = len(served_chats)

    status_msg = await RichParser.reply(
        message,
        f"⚡ *Memulai proses Global Ban untuk {target_user.mention} di `{total_chats}` grup...*"
    )

    banned_count = 0
    failed_count = 0
    start_time = time.time()
    last_update_time = 0

    for idx, chat_id in enumerate(served_chats, start=1):
        try:
            await client.ban_chat_member(chat_id, target_user.id)
            banned_count += 1
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            try:
                await client.ban_chat_member(chat_id, target_user.id)
                banned_count += 1
            except Exception:
                failed_count += 1
        except (ChatAdminRequired, ChatWriteForbidden, ChannelPrivate, UserAdminInvalid):
            failed_count += 1
        except Exception:
            failed_count += 1

        now = time.time()
        if (now - last_update_time >= 3.0) or (idx == total_chats):
            last_update_time = now
            prog_text = (
                f"⚡ *Proses Global Ban Berjalan...*\n\n"
                f"**> 👤 Target :** {target_user.mention} (`{target_user.id}`)\n"
                f"**> 📢 Kemajuan :** `{idx}` / `{total_chats}` grup\n"
                f"**> ✅ Berhasil Ban :** `{banned_count}` grup\n"
                f"**> ⚠️ Dilewati/Gagal :** `{failed_count}` grup"
            )
            try:
                await RichParser.edit(status_msg, prog_text)
            except Exception:
                pass

        await asyncio.sleep(0.04)

    total_elapsed = time.time() - start_time
    u_clean_name = clean_markdown(target_user.first_name or "Pengguna").replace("|", "\\|")
    banner_clean_name = clean_markdown(sender.first_name or "Admin").replace("|", "\\|")
    clean_reason = clean_markdown(reason).replace("|", "\\|")

    card = (
        "| ⛔ Global Ban Berhasil Dieksekusi |\n"
        "|:---:|\n"
        f"| {target_user.mention} telah di-banned secara global |\n\n"
        "| Parameter | Nilai Informasi |\n"
        "|:---|:---|\n"
        f"| 👤 Nama Pengguna | {u_clean_name} |\n"
        f"| 🆔 User ID | `{target_user.id}` |\n"
        f"| 📝 Alasan GBan | {clean_reason} |\n"
        f"| 👮 Penindak | {sender.mention} |\n"
        f"| 📢 Total Grup Diproses | `{total_chats}` grup |\n"
        f"| 🚫 Berhasil Di-Ban | `{banned_count}` grup |\n"
        f"| ⏱ Waktu Eksekusi | `{total_elapsed:.2f}` detik |\n"
        f"| 🛡 Status Keamanan | Masuk Blacklist Otomatis |\n\n"
        "| 🤖 Nusantara Stream 🤖 |\n"
        "|:---:|\n"
        "| |"
    )
    try:
        await RichParser.edit(status_msg, card)
    except Exception:
        await RichParser.reply(message, card)


@BOT("ungban", "unglobalban", "un_gban")
async def ungban_command(client: Client, message: Message):
    """[Sudo/Owner] Mencabut status Global Ban (GBan) dan meng-unban pengguna dari grup."""
    sender = message.from_user
    if not sender or not Config.is_sudo(sender.id):
        return await RichParser.reply(
            message,
            "❌ *Perintah ini hanya dapat digunakan oleh Sudo Admin atau Pemilik Bot.*"
        )

    target_user = None

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif len(message.command) > 1:
        user_input = message.command[1]
        if user_input.isdigit():
            user_input = int(user_input)
        try:
            target_user = await client.get_users(user_input)
        except Exception:
            return await RichParser.reply(message, "❌ *Pengguna tidak ditemukan atau ID tidak valid.*")

    if not target_user:
        guide_card = (
            "| ℹ️ Panduan Perintah Un-GBan |\n"
            "|:---:|\n"
            "| Mencabut larangan massal Global Ban pengguna |\n\n"
            "| Format Perintah | Keterangan |\n"
            "|:---|:---|\n"
            "| `/ungban` (balas pesan) | Un-GBan pengguna yang dibalas |\n"
            "| `/ungban @username` | Un-GBan via username |\n"
            "| `/ungban [user_id]` | Un-GBan via User ID |\n\n"
            "| 🤖 Nusantara Stream 🤖 |\n"
            "|:---:|\n"
            "| |"
        )
        return await RichParser.reply(message, guide_card)

    # Cek apakah user memang sedang di-GBan
    if not db.is_user_gbanned(target_user.id):
        return await RichParser.reply(
            message,
            f"ℹ️ {target_user.mention} *tidak terdaftar di dalam daftar Global Ban.*"
        )

    # Hapus dari database
    await db.remove_gban_user(target_user.id)

    served_chats = await db.get_served_chats()
    total_chats = len(served_chats)

    status_msg = await RichParser.reply(
        message,
        f"🔄 *Membuka blokir Global Ban untuk {target_user.mention} di `{total_chats}` grup...*"
    )

    unbanned_count = 0
    failed_count = 0
    start_time = time.time()
    last_update_time = 0

    for idx, chat_id in enumerate(served_chats, start=1):
        try:
            await client.unban_chat_member(chat_id, target_user.id)
            unbanned_count += 1
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            try:
                await client.unban_chat_member(chat_id, target_user.id)
                unbanned_count += 1
            except Exception:
                failed_count += 1
        except Exception:
            failed_count += 1

        now = time.time()
        if (now - last_update_time >= 3.0) or (idx == total_chats):
            last_update_time = now
            prog_text = (
                f"🔄 *Proses Un-GBan Berjalan...*\n\n"
                f"**> 👤 Target :** {target_user.mention} (`{target_user.id}`)\n"
                f"**> 📢 Kemajuan :** `{idx}` / `{total_chats}` grup\n"
                f"**> 🔓 Berhasil Unban :** `{unbanned_count}` grup"
            )
            try:
                await RichParser.edit(status_msg, prog_text)
            except Exception:
                pass

        await asyncio.sleep(0.04)

    total_elapsed = time.time() - start_time
    u_clean_name = clean_markdown(target_user.first_name or "Pengguna").replace("|", "\\|")

    card = (
        "| 🔓 Global Ban Berhasil Dicabut |\n"
        "|:---:|\n"
        f"| {target_user.mention} telah dihapus dari daftar Global Ban |\n\n"
        "| Parameter | Nilai Informasi |\n"
        "|:---|:---|\n"
        f"| 👤 Nama Pengguna | {u_clean_name} |\n"
        f"| 🆔 User ID | `{target_user.id}` |\n"
        f"| 👮 Pencabut GBan | {sender.mention} |\n"
        f"| 📢 Grup Ter-Unban | `{unbanned_count}` / `{total_chats}` grup |\n"
        f"| ⏱ Waktu Eksekusi | `{total_elapsed:.2f}` detik |\n"
        f"| 🛡 Status Keamanan | Diizinkan Kembali |\n\n"
        "| 🤖 Nusantara Stream 🤖 |\n"
        "|:---:|\n"
        "| |"
    )
    try:
        await RichParser.edit(status_msg, card)
    except Exception:
        await RichParser.reply(message, card)


@BOT("gbanlist", "gbans", "bannedlist")
async def gban_list_command(client: Client, message: Message):
    """[Sudo/Owner] Menampilkan daftar seluruh pengguna yang terkena Global Ban."""
    sender = message.from_user
    if not sender or not Config.is_sudo(sender.id):
        return await RichParser.reply(
            message,
            "❌ *Perintah ini hanya dapat digunakan oleh Sudo Admin atau Pemilik Bot.*"
        )

    gban_users = await db.get_gban_users()
    if not gban_users:
        return await RichParser.reply(
            message,
            "✅ *Tidak ada pengguna yang saat ini terdaftar di Global Ban.*"
        )

    total_banned = len(gban_users)
    text = (
        f"| ⛔ Daftar Pengguna Global Ban ({total_banned}) |\n"
        "|:---:|\n"
        "| Daftar blacklist pengguna berbahaya |\n\n"
        "| No | Pengguna | User ID | Alasan |\n"
        "|:---:|:---|:---:|:---|\n"
    )

    # Tampilkan maksimal 20 data teratas
    for idx, u in enumerate(gban_users[:20], start=1):
        u_id = u.get("user_id", 0)
        u_name = clean_markdown(u.get("first_name", "Pengguna")[:14]).replace("|", "\\|")
        reason = clean_markdown(u.get("reason", "Tanpa alasan")[:20]).replace("|", "\\|")
        text += f"| #{idx} | {u_name} | `{u_id}` | {reason} |\n"

    if total_banned > 20:
        text += f"\n*...dan {total_banned - 20} pengguna lainnya.*\n"

    text += (
        "\n| 🤖 Nusantara Stream 🤖 |\n"
        "|:---:|\n"
        "| |"
    )
    await RichParser.reply(message, text)


@BOT.on_message(filters.group & filters.new_chat_members)
async def gban_auto_kick_listener(client: Client, message: Message):
    """Otomatis memblokir & mengeluarkan user Global Ban yang mencoba bergabung ke grup."""
    if not message.new_chat_members:
        return

    chat = message.chat
    for member in message.new_chat_members:
        if db.is_user_gbanned(member.id):
            try:
                # Ban user dari grup
                await client.ban_chat_member(chat.id, member.id)

                gban_info = await db.get_gban_user(member.id)
                reason = gban_info.get("reason", "Pelanggaran aturan global") if gban_info else "Pelanggaran aturan global"
                m_name = clean_markdown(member.first_name or "Pengguna").replace("|", "\\|")
                clean_reason = clean_markdown(reason).replace("|", "\\|")

                alert_card = (
                    "| 🚨 Terdeteksi Pengguna Global Banned |\n"
                    "|:---:|\n"
                    f"| {member.mention} otomatis dikeluarkan dari grup |\n\n"
                    "| Parameter | Keterangan |\n"
                    "|:---|:---|\n"
                    f"| 👤 Nama Pengguna | {m_name} |\n"
                    f"| 🆔 User ID | `{member.id}` |\n"
                    f"| 📝 Alasan GBan | {clean_reason} |\n"
                    f"| 🛡 Tindakan | Dikeluarkan Otomatis (Auto-Ban) |\n\n"
                    "| 🤖 Nusantara Stream 🤖 |\n"
                    "|:---:|\n"
                    "| |"
                )
                await RichParser.reply(message, alert_card)
                logger.info(f"Auto-banned GBan user {member.id} in chat {chat.id}")
            except Exception as e:
                logger.debug(f"Gagal auto-ban user GBan {member.id} di chat {chat.id}: {e}")
