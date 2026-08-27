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
import datetime
import os
import shutil
import logging
import glob
import importlib
import sys
import json
import re
import math
import random
import platform
import traceback
import io

try:
    from kurigram import Client, filters, enums, types, errors
    from kurigram.types import (
        Message,
        ReplyParameters,
        InlineKeyboardMarkup,
        InlineKeyboardButton,
        CallbackQuery,
        InputMediaPhoto,
        InputMediaVideo,
        InputMediaAudio,
        InputMediaDocument,
        LinkPreviewOptions,
    )
    from kurigram.enums import ParseMode, ChatMemberStatus, ChatType
    from kurigram.errors import (
        FloodWait,
        UserIsBlocked,
        InputUserDeactivated,
        PeerIdInvalid,
        ChatAdminRequired,
        ChatWriteForbidden,
        ChannelPrivate,
    )
except ImportError:
    from pyrogram import Client, filters, enums, types, errors
    from pyrogram.types import (
        Message,
        ReplyParameters,
        InlineKeyboardMarkup,
        InlineKeyboardButton,
        CallbackQuery,
        InputMediaPhoto,
        InputMediaVideo,
        InputMediaAudio,
        InputMediaDocument,
        LinkPreviewOptions,
    )
    from pyrogram.enums import ParseMode, ChatMemberStatus, ChatType
    try:
        from pyrogram.errors import (
            FloodWait,
            UserIsBlocked,
            InputUserDeactivated,
            PeerIdInvalid,
            ChatAdminRequired,
            ChatWriteForbidden,
            ChannelPrivate,
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

        class ParseMode:
            HTML = "html"
            MARKDOWN = "markdown"

        class ReplyParameters:
            def __init__(self, message_id: int, **kwargs):
                self.message_id = message_id

from config import Config
from utils.decorators import (
    add_authorized_user,
    remove_authorized_user,
    get_authorized_users,
)
from utils.queue import queue_manager
from utils.formatters import (
    clean_markdown,
    format_broadcast_progress_card,
    format_broadcast_finished_card,
    human_readable_size,
)
from utils.rich_parser import RichParser
from utils.database import db
from utils.keyboards import (
    ButtonStyle,
    get_control_panel,
    get_control_panel_video,
    get_start_keyboard,
    get_help_keyboard,
)

logger = logging.getLogger("NusantaraStream.Admin")


@Client.on_message(filters.command(["auth"]) & ~filters.forwarded)
async def auth_user_command(client: Client, message: Message):
    """Memberikan izin khusus kepada user untuk mengontrol bot."""
    chat = message.chat
    sender = message.from_user

    # Cek apakah pengirim adalah admin/owner grup atau sudo
    if sender.id not in Config.SUDO_USERS:
        member = await chat.get_member(sender.id)
        if member.status not in (
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR,
        ):
            return await RichParser.reply(
                message,
                "❌ *Hanya Admin Grup yang dapat menggunakan perintah ini.*"
            )

    target_user = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            target_user = await client.get_users(message.command[1])
        except Exception:
            return await RichParser.reply(message, "❌ *Pengguna tidak ditemukan.*")

    if not target_user:
        return await RichParser.reply(
            message,
            "ℹ️ **Cara Penggunaan:**\n"
            "> - Balas pesan user dengan `/auth`\n"
            "> - Ketik `/auth @username` atau `/auth [User ID]`"
        )

    add_authorized_user(chat.id, target_user.id)
    await RichParser.reply(
        message,
        f"✅ **Pengguna Diizinkan:** {target_user.mention} sekarang dapat mengontrol pemutaran musik di grup ini."
    )


@Client.on_message(filters.command(["unauth"]) & ~filters.forwarded)
async def unauth_user_command(client: Client, message: Message):
    """Mencabut izin khusus user di grup."""
    chat = message.chat
    sender = message.from_user

    if sender.id not in Config.SUDO_USERS:
        member = await chat.get_member(sender.id)
        if member.status not in (
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR,
        ):
            return await RichParser.reply(
                message,
                "❌ *Hanya Admin Grup yang dapat menggunakan perintah ini.*"
            )

    target_user = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            target_user = await client.get_users(message.command[1])
        except Exception:
            return await RichParser.reply(message, "❌ *Pengguna tidak ditemukan.*")

    if not target_user:
        return await RichParser.reply(
            message,
            "ℹ️ **Cara Penggunaan:**\n"
            "> - Balas pesan user dengan `/unauth`\n"
            "> - Ketik `/unauth @username` atau `/unauth [User ID]`"
        )

    remove_authorized_user(chat.id, target_user.id)
    await RichParser.reply(
        message,
        f"🗑 **Izin Dicabut:** {target_user.mention} tidak lagi memiliki izin khusus."
    )


@Client.on_message(filters.command(["authlist"]) & ~filters.forwarded)
async def authlist_command(client: Client, message: Message):
    """Melihat daftar user terotorisasi di grup saat ini."""
    chat_id = message.chat.id
    users = get_authorized_users(chat_id)

    if not users:
        text = (
            "| 📋 Daftar Pengguna Terotorisasi |\n"
            "|:---:|\n"
            "| Tidak ada pengguna khusus yang terdaftar |\n\n"
            "| Informasi Akses | Keterangan |\n"
            "|:---|:---|\n"
            "| 🛡 Status Akses | Hanya Admin Grup yang memiliki kontrol pemutar |\n\n"
            "| 🤖 Nusantara Stream 🤖 |\n"
            "|:---:|\n"
            "| |"
        )
        return await RichParser.reply(message, text)

    text = (
        "| 📋 Daftar Pengguna Terotorisasi |\n"
        "|:---:|\n"
        "| Pengguna dengan izin kontrol pemutar bot di grup ini |\n\n"
        "| No | Pengguna | User ID |\n"
        "|:---:|:---|:---:|\n"
    )
    for idx, uid in enumerate(users, start=1):
        try:
            u = await client.get_users(uid)
            u_name = clean_markdown(u.first_name).replace("|", "\\|")
            text += f"| #{idx} | [{u_name}](tg://user?id={uid}) | `{uid}` |\n"
        except Exception:
            text += f"| #{idx} | Pengguna | `{uid}` |\n"

    text += (
        "\n| 🤖 Nusantara Stream 🤖 |\n"
        "|:---:|\n"
        "| |"
    )
    await RichParser.reply(message, text)


@Client.on_message(filters.command(["activevc"]) & filters.user(Config.SUDO_USERS))
async def active_vc_command(client: Client, message: Message):
    """[Sudo] Melihat seluruh voice chat yang sedang aktif memutar musik."""
    active_chats = queue_manager.get_active_chats()

    if not active_chats:
        text = (
            "| 🔊 Status Voice Chat Aktif |\n"
            "|:---:|\n"
            "| Saat ini tidak ada Voice Chat yang aktif |\n\n"
            "| 🤖 Nusantara Stream 🤖 |\n"
            "|:---:|\n"
            "| |"
        )
        return await RichParser.reply(message, text)

    text = (
        f"| 🔊 Daftar Voice Chat Aktif ({len(active_chats)} Grup) |\n"
        f"|:---:|\n"
        f"| Obrolan suara yang sedang aktif memutar media |\n\n"
        f"| No | Grup | Media Sedang Diputar |\n"
        f"|:---:|:---|:---|\n"
    )
    for idx, cid in enumerate(active_chats, start=1):
        track = queue_manager.get_current_track(cid)
        title = clean_markdown(track.title[:25] if track else "Tidak Diketahui").replace("|", "\\|")
        try:
            chat = await client.get_chat(cid)
            c_name = clean_markdown(chat.title[:20]).replace("|", "\\|")
        except Exception:
            c_name = f"Chat {cid}"

        text += f"| #{idx} | {c_name} | [{title}]({track.url if track else 'https://youtube.com'}) |\n"

    text += (
        "\n| 🤖 Nusantara Stream 🤖 |\n"
        "|:---:|\n"
        "| |"
    )
    await RichParser.reply(message, text)


@Client.on_message(filters.command(["clean"]) & filters.user(Config.SUDO_USERS))
async def clean_cache_command(client: Client, message: Message):
    """[Sudo] Membersihkan cache dan file sementara di server."""
    reply = await RichParser.reply(message, "⚡ *Membersihkan direktori cache & temp...*")

    try:
        deleted_count = 0
        for folder in [Config.TEMP_DIR, Config.CACHE_DIR]:
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                        deleted_count += 1
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                        deleted_count += 1
                except Exception as e:
                    logger.debug(f"Gagal hapus {file_path}: {e}")

        clean_text = (
            "| ✨ Pembersihan Server Selesai |\n"
            "|:---:|\n"
            "| Pembersihan cache dan media sementara berhasil |\n\n"
            "| Kategori | Detail Pembersihan |\n"
            "|:---|:---|\n"
            f"| 🗑 File Dihapus | `{deleted_count}` file |\n"
            "| 📁 Direktori | Cache & Temp Directories |\n\n"
            "| 🤖 Nusantara Stream 🤖 |\n"
            "|:---:|\n"
            "| |"
        )
        await RichParser.edit(reply, clean_text)
    except Exception as e:
        await RichParser.edit(
            reply,
            f"❌ **Gagal membersihkan cache:** `{clean_markdown(str(e))}`"
        )


@Client.on_message(
    filters.command(["backup", "backupdb"])
    & filters.user(Config.OWNER_ID)
    & ~filters.forwarded
)
async def backup_db_command(client: Client, message: Message):
    """[Owner Only] Mengunduh berkas cadangan database SQLite lengkap."""
    import datetime

    status_msg = await RichParser.reply(message, "📦 *Membuat cadangan database SQLite...*")

    summary = await db.get_db_summary()
    db_path = summary.get("db_path", "")

    if not os.path.exists(db_path):
        return await RichParser.edit(status_msg, "❌ *Berkas database tidak ditemukan.*")

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_date = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"nusantara_backup_{file_date}.db"

    u_cnt = summary.get("users", 0)
    c_cnt = summary.get("chats", 0)
    s_cnt = summary.get("sudos", 0)
    p_cnt = summary.get("playlists", 0)
    size_str = human_readable_size(summary.get("size_bytes", 0))

    caption_card = (
        "💾 **Cadangan Database Nusantara Stream**\n"
        f"🕒 *Waktu Backup:* `{now_str}`\n\n"
        "**> 📊 Ringkasan Metrik Database:**\n"
        f"**> 👥 Pengguna Terlayani :** `{u_cnt:,}` pengguna\n"
        f"**> 📢 Grup Terlayani     :** `{c_cnt:,}` grup\n"
        f"**> 🛡️ Sudo Admin        :** `{s_cnt}` admin\n"
        f"**> 📂 Lagu di Playlist   :** `{p_cnt:,}` lagu\n"
        f"**> 💾 Ukuran Berkas      :** `{size_str}`\n\n"
        "💡 *Untuk memulihkan:* Balas berkas ini dengan `/restore`"
    )

    try:
        await client.send_document(
            chat_id=message.chat.id,
            document=db_path,
            file_name=backup_name,
            caption=caption_card,
            parse_mode=ParseMode.MARKDOWN,
            reply_parameters=ReplyParameters(message_id=message.id),
        )
        await status_msg.delete()
    except Exception as e:
        logger.error(f"Gagal mengirim backup db: {e}")
        await RichParser.edit(status_msg, f"❌ **Gagal mengirim berkas backup:** `{clean_markdown(str(e))}`")


@Client.on_message(
    filters.command(["restore", "restoredb"])
    & filters.user(Config.OWNER_ID)
    & ~filters.forwarded
)
async def restore_db_command(client: Client, message: Message):
    """[Owner Only] Memulihkan database dari berkas SQLite (.db) yang dibalas."""
    reply = message.reply_to_message
    if not reply or not reply.document:
        return await RichParser.reply(
            message,
            "ℹ️ **Cara Pemulihan Database:**\n"
            "> Balas (reply) ke berkas database `.db` yang dikirim bot dengan perintah `/restore`.",
        )

    doc = reply.document
    if not doc.file_name or not doc.file_name.endswith(".db"):
        return await RichParser.reply(
            message,
            "❌ **Format Berkas Tidak Valid:**\n"
            "> Berkas yang dibalas harus berekstensi `.db` hasil dari `/backup`.",
        )

    status_msg = await RichParser.reply(message, "⏳ *Mengunduh dan memverifikasi berkas database...*")

    temp_restore_path = os.path.join(Config.TEMP_DIR, f"restore_{doc.file_name}")
    try:
        await client.download_media(message=reply, file_name=temp_restore_path)

        ok, result = await db.validate_and_restore_db(temp_restore_path)
        if not ok:
            return await RichParser.edit(
                status_msg,
                f"❌ **Gagal Memulihkan Database:**\n> {result}",
            )

        # Refresh SUDO_USERS dari database yang dipulihkan
        db_sudos = await db.get_sudo_users()
        Config.SUDO_USERS = list(set([Config.OWNER_ID] + db_sudos)) if Config.OWNER_ID else db_sudos

        card = (
            "| ✅ Pemulihan Database Berhasil |\n"
            "|:---:|\n"
            "| Seluruh data berhasil dipulihkan dari cadangan |\n\n"
            "| Metrik Terpulihkan | Jumlah Data |\n"
            "|:---|:---|\n"
            f"| 👥 Pengguna | `{result.get('users', 0):,}` pengguna |\n"
            f"| 📢 Grup | `{result.get('chats', 0):,}` grup |\n"
            f"| 🛡️ Sudo Admin | `{result.get('sudos', 0)}` admin |\n"
            f"| 📂 Lagu Playlist | `{result.get('playlists', 0):,}` lagu |\n\n"
            "| 🤖 Nusantara Stream 🤖 |\n"
            "|:---:|\n"
            "| |"
        )
        await RichParser.edit(status_msg, card)
    except Exception as e:
        logger.error(f"Restore error: {e}")
        await RichParser.edit(status_msg, f"❌ **Gagal memulihkan database:** `{clean_markdown(str(e))}`")
    finally:
        if os.path.exists(temp_restore_path):
            try:
                os.remove(temp_restore_path)
            except Exception:
                pass


@Client.on_message(
    filters.command(["broadcast", "gcast", "bcast"])
    & filters.user(Config.SUDO_USERS)
    & ~filters.forwarded
)
async def broadcast_command(client: Client, message: Message):
    """[Sudo] Mengirimkan pesan broadcast massal ke pengguna atau grup."""
    flags = [arg.lower() for arg in message.command[1:] if arg.startswith("-")]

    # Tentukan tipe target
    if "-users" in flags or "-user" in flags or "-u" in flags:
        target_label = "Pengguna (Private Chat)"
        targets = await db.get_served_users()
    elif "-groups" in flags or "-group" in flags or "-gc" in flags or "-g" in flags:
        target_label = "Grup Obrolan"
        targets = await db.get_served_chats()
    else:
        target_label = "Semua (Grup + Pengguna)"
        users = await db.get_served_users()
        chats = await db.get_served_chats()
        targets = list(set(users + chats))

    # Tentukan konten yang akan dikirim
    to_reply = message.reply_to_message
    broadcast_text = None

    if not to_reply:
        # Ambil teks argumen selain flag
        text_parts = [
            arg for arg in message.command[1:] if not arg.startswith("-")
        ]
        if not text_parts:
            guide_card = (
                "| 📢 Panduan Penggunaan Perintah Broadcast |\n"
                "|:---:|\n"
                "| Format pengiriman pesan massal ke pengguna & grup |\n\n"
                "| Target Flag | Keterangan Perintah |\n"
                "|:---|:---|\n"
                "| `/broadcast -all <pesan>` | Kirim ke SEMUA (Grup & Pengguna) |\n"
                "| `/broadcast -groups <pesan>` | Kirim ke SEMUA GRUP |\n"
                "| `/broadcast -users <pesan>` | Kirim ke SEMUA PENGGUNA |\n\n"
                "| 💡 Tips: Balas pesan/media apapun dengan `/broadcast -all` untuk meneruskan foto/video/tombol! |\n"
                "|:---:|\n"
                "| |"
            )
            return await RichParser.reply(message, guide_card)
        broadcast_text = " ".join(text_parts)

    if not targets:
        return await RichParser.reply(
            message,
            f"❌ *Tidak ada target {target_label} yang tersimpan di database.*"
        )

    total_targets = len(targets)
    status_card = format_broadcast_progress_card(
        target_type=target_label,
        current=0,
        total=total_targets,
        success=0,
        failed=0,
    )
    status_msg = await RichParser.reply(message, status_card)

    start_time = time.time()
    last_update_time = 0
    success = 0
    failed = 0

    for idx, target_id in enumerate(targets, start=1):
        try:
            if to_reply:
                await to_reply.copy(chat_id=target_id)
            else:
                await RichParser.send(
                    client,
                    chat_id=target_id,
                    text=broadcast_text,
                )
            success += 1
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            try:
                if to_reply:
                    await to_reply.copy(chat_id=target_id)
                else:
                    await RichParser.send(
                        client,
                        chat_id=target_id,
                        text=broadcast_text,
                    )
                success += 1
            except Exception:
                failed += 1
        except (UserIsBlocked, InputUserDeactivated):
            await db.remove_served_user(target_id)
            failed += 1
        except (ChatAdminRequired, ChatWriteForbidden, ChannelPrivate):
            await db.remove_served_chat(target_id)
            failed += 1
        except Exception as e:
            logger.debug(f"Broadcast gagal ke {target_id}: {e}")
            failed += 1

        # Pembaruan UI progres setiap 3 detik atau selesai
        now = time.time()
        if (now - last_update_time >= 3.0) or (idx == total_targets):
            last_update_time = now
            elapsed = max(0.1, now - start_time)
            speed = idx / elapsed
            eta = int((total_targets - idx) / speed) if speed > 0 else 0
            prog_card = format_broadcast_progress_card(
                target_type=target_label,
                current=idx,
                total=total_targets,
                success=success,
                failed=failed,
                speed=speed,
                eta=eta,
            )
            try:
                await RichParser.edit(status_msg, prog_card)
            except Exception:
                pass

        # Jeda interval mikro untuk menjaga kelancaran koneksi
        await asyncio.sleep(0.08)

    total_elapsed = time.time() - start_time
    finished_card = format_broadcast_finished_card(
        target_type=target_label,
        total=total_targets,
        success=success,
        failed=failed,
        elapsed_sec=total_elapsed,
    )
    try:
        await RichParser.edit(status_msg, finished_card)
    except Exception:
        await RichParser.reply(message, finished_card)


@Client.on_message(
    filters.command(["addsudo", "promotesudo"])
    & ~filters.forwarded
)
async def add_sudo_command(client: Client, message: Message):
    """[Owner Only] Menambahkan user ke daftar Sudo Admin bot."""
    sender = message.from_user
    if not sender or not Config.is_owner(sender.id):
        return await RichParser.reply(
            message,
            "❌ *Perintah ini hanya dapat digunakan oleh Pemilik (Owner) Bot.*"
        )

    target_user = None
    
    # 1. Cek jika perintah membalas (reply) ke pesan user
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    
    # 2. Cek jika ada argumen ID atau Username/Mention setelah command
    elif len(message.command) > 1:
        user_input = message.command[1]
        
        # Konversi ke integer jika input berupa angka (User ID)
        if user_input.isdigit():
            user_input = int(user_input)
            
        try:
            target_user = await client.get_users(user_input)
        except Exception:
            return await RichParser.reply(message, "❌ *Pengguna tidak ditemukan.*")

    # 3. Validasi jika target user tidak ditemukan/input kosong
    if not target_user:
        return await RichParser.reply(
            message,
            "ℹ️ **Cara Penggunaan:**\n"
            "> - Balas pesan user dengan `/addsudo`\n"
            "> - Ketik `/addsudo @username` atau `/addsudo [User ID]`"
        )

    if target_user.id == Config.OWNER_ID or Config.is_developer(target_user.id):
        return await RichParser.reply(message, "👑 *Pengguna tersebut adalah Pemilik (Owner) / Developer Bot.*")

    if target_user.id in Config.SUDO_USERS:
        return await RichParser.reply(message, f"ℹ️ {target_user.mention} *sudah terdaftar sebagai Sudo Admin.*")

    await db.add_sudo(target_user.id)
    if target_user.id not in Config.SUDO_USERS:
        Config.SUDO_USERS.append(target_user.id)

    u_name = clean_markdown(target_user.first_name).replace("|", "\\|")
    card = (
        "| 👑 Sudo Admin Baru Ditambahkan |\n"
        "|:---:|\n"
        f"| {target_user.mention} resmi menjadi Sudo Admin |\n\n"
        "| Parameter | Nilai |\n"
        "|:---|:---|\n"
        f"| 👤 Nama | {u_name} |\n"
        f"| 🆔 User ID | `{target_user.id}` |\n"
        f"| 🛡 Hak Akses | Sudo Administrator |\n\n"
        "| 🤖 Nusantara Stream 🤖 |\n"
        "|:---:|\n"
        "| |"
    )
    await RichParser.reply(message, card)


@Client.on_message(
    filters.command(["delsudo", "removesudo", "demotesudo"])
    & ~filters.forwarded
)
async def del_sudo_command(client: Client, message: Message):
    """[Owner Only] Mencabut izin Sudo Admin dari user."""
    sender = message.from_user
    if not sender or not Config.is_owner(sender.id):
        return await RichParser.reply(
            message,
            "❌ *Perintah ini hanya dapat digunakan oleh Pemilik (Owner) Bot.*"
        )

    target_user = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            target_user = await client.get_users(message.command[1])
        except Exception:
            return await RichParser.reply(message, "❌ *Pengguna tidak ditemukan.*")

    if not target_user:
        return await RichParser.reply(
            message,
            "ℹ️ **Cara Penggunaan:**\n"
            "> - Balas pesan user dengan `/delsudo`\n"
            "> - Ketik `/delsudo @username` atau `/delsudo [User ID]`"
        )

    if target_user.id == Config.OWNER_ID:
        return await RichParser.reply(message, "❌ *Tidak dapat mencabut status Owner Bot.*")

    if Config.is_developer(target_user.id) or target_user.id in Config.DEVELOPER_IDS:
        return await RichParser.reply(message, "❌ *Tidak dapat mencabut izin Developer / Pembuat Asli Bot.*")

    if target_user.id not in Config.SUDO_USERS:
        return await RichParser.reply(message, f"❌ {target_user.mention} *bukan merupakan Sudo Admin.*")

    await db.remove_sudo(target_user.id)
    if target_user.id in Config.SUDO_USERS:
        Config.SUDO_USERS.remove(target_user.id)

    u_name = clean_markdown(target_user.first_name).replace("|", "\\|")
    card = (
        "| 🗑 Izin Sudo Admin Dicabut |\n"
        "|:---:|\n"
        f"| {target_user.mention} telah dihapus dari daftar Sudo |\n\n"
        "| Parameter | Nilai |\n"
        "|:---|:---|\n"
        f"| 👤 Nama | {u_name} |\n"
        f"| 🆔 User ID | `{target_user.id}` |\n"
        f"| 🛡 Status | Pengguna Reguler |\n\n"
        "| 🤖 Nusantara Stream 🤖 |\n"
        "|:---:|\n"
        "| |"
    )
    await RichParser.reply(message, card)


@Client.on_message(
    filters.command(["sudolist", "sudos"])
    & filters.user(Config.SUDO_USERS)
    & ~filters.forwarded
)
async def sudo_list_command(client: Client, message: Message):
    """[Sudo] Menampilkan daftar seluruh Sudo Users dan Owner."""
    db_sudos = await db.get_sudos()
    all_sudos = list(set(Config.SUDO_USERS + db_sudos))

    text = (
        "| 👑 Daftar Pengelola & Sudo Admin |\n"
        "|:---:|\n"
        "| Tim manajemen otoritas bot |\n\n"
        "| No | Pengguna | Role | User ID |\n"
        "|:---:|:---|:---:|:---:|\n"
    )

    idx = 1
    # Owner first
    if Config.OWNER_ID:
        try:
            owner_user = await client.get_users(Config.OWNER_ID)
            o_name = clean_markdown(owner_user.first_name[:18]).replace("|", "\\|")
        except Exception:
            o_name = "Owner"
        text += f"| #{idx} | {o_name} | 👑 Owner | `{Config.OWNER_ID}` |\n"
        idx += 1

    # Sudo users
    for uid in all_sudos:
        if uid == Config.OWNER_ID:
            continue
        try:
            u = await client.get_users(uid)
            u_name = clean_markdown(u.first_name[:18]).replace("|", "\\|")
        except Exception:
            u_name = f"User {uid}"
        text += f"| #{idx} | {u_name} | 🛡 Sudo | `{uid}` |\n"
        idx += 1

    text += (
        "\n| 🤖 Nusantara Stream 🤖 |\n"
        "|:---:|\n"
        "| |"
    )
    await RichParser.reply(message, text)


# Track file modification times for Hot Reload detection
_LOADED_FILE_MTIMES: dict[str, float] = {}
for _pattern in ["plugins/*.py", "utils/*.py", "core/*.py", "config.py"]:
    for _f in glob.glob(_pattern):
        try:
            _LOADED_FILE_MTIMES[_f] = os.path.getmtime(_f)
        except Exception:
            pass


@Client.on_message(
    filters.command(["reload", "refresh"])
    & filters.user(Config.SUDO_USERS)
    & ~filters.forwarded
)
async def reload_plugins_command(client: Client, message: Message):
    """[Sudo] Muat ulang (Hot Reload) kode plugin & utils tanpa mematikan bot atau koneksi Telegram."""
    reply = await RichParser.reply(message, "⚡ *Memuat ulang seluruh modul sistem (Hot Reload)...*")
    
    import importlib
    import glob
    import sys

    reloaded = []
    errors = []
    modified_files = []

    # 0. Reload config module & deteksi perubahan
    if os.path.exists("config.py"):
        try:
            curr_mtime = os.path.getmtime("config.py")
            last_mtime = _LOADED_FILE_MTIMES.get("config.py")
            if last_mtime is None:
                modified_files.append(("config.py", "🆕 Baru"))
            elif curr_mtime > last_mtime:
                modified_files.append(("config.py", "✏️ Diubah"))
            _LOADED_FILE_MTIMES["config.py"] = curr_mtime

            if "config" in sys.modules:
                importlib.reload(sys.modules["config"])
            else:
                importlib.import_module("config")
        except Exception as e:
            errors.append(f"config: {e}")

    # 1. Bersihkan seluruh handler lama di dispatcher agar tidak duplikat
    if hasattr(client, "dispatcher") and hasattr(client.dispatcher, "groups"):
        client.dispatcher.groups.clear()

    # 2. Reload utils modules & deteksi perubahan
    for py_file in sorted(glob.glob("utils/*.py")):
        mod_name = py_file.replace("/", ".").replace(".py", "")
        if mod_name.endswith("__init__"):
            continue

        try:
            curr_mtime = os.path.getmtime(py_file)
            last_mtime = _LOADED_FILE_MTIMES.get(py_file)
            if last_mtime is None:
                modified_files.append((py_file, "🆕 Baru"))
            elif curr_mtime > last_mtime:
                modified_files.append((py_file, "✏️ Diubah"))
            _LOADED_FILE_MTIMES[py_file] = curr_mtime

            if mod_name in sys.modules:
                importlib.reload(sys.modules[mod_name])
            else:
                importlib.import_module(mod_name)
        except Exception as e:
            errors.append(f"{mod_name}: {e}")

    # 3. Reload core modules jika perlu & deteksi perubahan
    for py_file in sorted(glob.glob("core/*.py")):
        mod_name = py_file.replace("/", ".").replace(".py", "")
        if mod_name.endswith("__init__"):
            continue

        try:
            curr_mtime = os.path.getmtime(py_file)
            last_mtime = _LOADED_FILE_MTIMES.get(py_file)
            if last_mtime is None:
                modified_files.append((py_file, "🆕 Baru"))
            elif curr_mtime > last_mtime:
                modified_files.append((py_file, "✏️ Diubah"))
            _LOADED_FILE_MTIMES[py_file] = curr_mtime

            if mod_name in sys.modules:
                importlib.reload(sys.modules[mod_name])
        except Exception:
            pass

    # 4. Reload dan daftarkan kembali seluruh handler dari setiap plugin ke client dispatcher
    for py_file in sorted(glob.glob("plugins/*.py")):
        mod_name = py_file.replace("/", ".").replace(".py", "")
        if mod_name.endswith("__init__"):
            continue

        try:
            curr_mtime = os.path.getmtime(py_file)
            last_mtime = _LOADED_FILE_MTIMES.get(py_file)
            if last_mtime is None:
                modified_files.append((py_file, "🆕 Baru"))
            elif curr_mtime > last_mtime:
                modified_files.append((py_file, "✏️ Diubah"))
            _LOADED_FILE_MTIMES[py_file] = curr_mtime

            if mod_name in sys.modules:
                module = importlib.reload(sys.modules[mod_name])
            else:
                module = importlib.import_module(mod_name)

            # Re-register handlers from module into client dispatcher
            for name in vars(module).keys():
                obj = getattr(module, name)
                if hasattr(obj, "handlers") and isinstance(obj.handlers, list):
                    for item in obj.handlers:
                        if isinstance(item, tuple) and len(item) == 2:
                            client.add_handler(item[0], item[1])

            reloaded.append(mod_name.split(".")[-1])
        except Exception as e:
            errors.append(f"{mod_name}: {e}")

    # Format bagian berkas yang diubah
    if modified_files:
        changes_section = "| 📝 Berkas Diperbarui | 💾 Ukuran | 🔄 Status |\n|:---|:---:|:---:|\n"
        for fpath, fstatus in modified_files:
            clean_p = f"`{fpath}`"
            fsize = human_readable_size(os.path.getsize(fpath)) if os.path.exists(fpath) else "-"
            changes_section += f"| {clean_p} | `{fsize}` | {fstatus} |\n"
        changes_section += "\n"
    else:
        changes_section = (
            "| ℹ️ Seluruh berkas sudah dalam versi terbaru (tidak ada perubahan kode). |\n"
            "|:---:|\n"
            "| |\n\n"
        )

    err_text = f"| ⚠️ Peringatan | `{len(errors)} error` |\n" if errors else ""

    card = (
        "| ⚡ Hasil Hot Reload Sistem |\n"
        "|:---:|\n"
        "| Pembaruan modul berhasil tanpa memutus koneksi bot |\n\n"
        f"{changes_section}"
        "| Ringkasan Status | Nilai |\n"
        "|:---|:---|\n"
        f"| 📦 Total Modul Dipindai | `{len(reloaded)} plugin` |\n"
        f"| ✏️ Berkas Baru / Diubah | `{len(modified_files)} berkas` |\n"
        f"| ⏱ Status Koneksi | 🟢 Tetap Aktif (0x Reconnect) |\n"
        f"| 🛡 Risiko FloodWait | 0% (Koneksi MTProto Stabil) |\n"
        f"{err_text}"
        "\n| 🤖 Nusantara Stream 🤖 |\n"
        "|:---:|\n"
        "| |"
    )
    await RichParser.edit(reply, card)


@Client.on_message(
    filters.command(["restart", "reboot"])
    & filters.user(Config.SUDO_USERS)
    & ~filters.forwarded
)
async def restart_bot_command(client: Client, message: Message):
    """[Sudo] Memulai ulang (restart) bot secara graceful."""
    reply = await RichParser.reply(message, "🔄 *Memulai prosedur restart sistem...*")
    await asyncio.sleep(1)

    card = (
        "| 🔄 Sistem Sedang Dimuat Ulang |\n"
        "|:---:|\n"
        "| Bot akan segera online kembali dalam beberapa detik |\n\n"
        "| 🤖 Nusantara Stream 🤖 |\n"
        "|:---:|\n"
        "| |"
    )
    try:
        await RichParser.edit(reply, card)
    except Exception:
        pass

    import sys
    os.execv(sys.executable, [sys.executable, "main.py"])


@Client.on_message(
    filters.command(["logs", "log"])
    & filters.user(Config.SUDO_USERS)
    & ~filters.forwarded
)
async def get_logs_command(client: Client, message: Message):
    """[Sudo] Mengambil file log aktivitas sistem bot."""
    log_file = "nusantara_stream.log"
    if not os.path.exists(log_file):
        return await RichParser.reply(message, "❌ *File log aktivitas belum tersedia.*")

    status = await RichParser.reply(message, "📄 *Mengirimkan file log sistem...*")
    try:
        await client.send_document(
            chat_id=message.chat.id,
            document=log_file,
            caption=(
                "| 📄 Nusantara Stream Activity Log |\n"
                "|:---:|\n"
                "| Catatan log aktivitas server terbaru |"
            ),
        )
        await status.delete()
    except Exception as e:
        await RichParser.edit(status, f"❌ **Gagal mengirim log:** `{clean_markdown(str(e))}`")


@Client.on_message(
    filters.command(["sysinfo", "server"])
    & filters.user(Config.SUDO_USERS)
    & ~filters.forwarded
)
async def sysinfo_command(client: Client, message: Message):
    """[Sudo] Menampilkan informasi statistik server & hardware."""
    import platform
    import sys
    try:
        import psutil
        cpu_pct = f"{psutil.cpu_percent(interval=0.5)}%"
        ram = psutil.virtual_memory()
        ram_used = f"{ram.used / (1024**3):.2f} GB / {ram.total / (1024**3):.2f} GB ({ram.percent}%)"
        disk = psutil.disk_usage("/")
        disk_used = f"{disk.used / (1024**3):.2f} GB / {disk.total / (1024**3):.2f} GB ({disk.percent}%)"
    except Exception:
        cpu_pct = "Tersedia"
        ram_used = "Tersedia"
        disk_used = "Tersedia"

    card = (
        "| 🖥 Informasi Status Server & Hardware |\n"
        "|:---:|\n"
        "| Metrik performa server Nusantara Stream |\n\n"
        "| Komponen | Status Spesifikasi |\n"
        "|:---|:---|\n"
        f"| 💻 OS | `{platform.system()} {platform.release()}` |\n"
        f"| 🐍 Python | `v{sys.version.split()[0]}` |\n"
        f"| ⚡ CPU Load | `{cpu_pct}` |\n"
        f"| 💾 RAM | `{ram_used}` |\n"
        f"| 💽 Disk Storage | `{disk_used}` |\n"
        f"| 🤖 Bot Engine | `Kurigram + PyTgCalls v2.3.3` |\n\n"
        "| 🤖 Nusantara Stream 🤖 |\n"
        "|:---:|\n"
        "| |"
    )
    await RichParser.reply(message, card)


@Client.on_message(
    filters.command(["eval", "sh", "exec"])
    & filters.user(Config.OWNER_ID)
    & ~filters.forwarded
)
async def eval_command(client: Client, message: Message):
    """[Owner Only] Mengeksekusi Python script atau shell command secara langsung dengan lingkungan pre-imported lengkap."""
    if len(message.command) < 2:
        return await RichParser.reply(message, "ℹ️ **Format:** `/eval <kode_python>` atau `/sh <perintah_bash>`")

    cmd = message.command[0].lower()
    code = message.text.split(None, 1)[1].strip()
    status_msg = await RichParser.reply(message, "⚡ *Mengeksekusi...*")

    if cmd == "sh":
        try:
            proc = await asyncio.create_subprocess_shell(
                code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            out = stdout.decode().strip() or stderr.decode().strip() or "Selesai tanpa output."
            if len(out) > 3000:
                out = out[:3000] + "... (dipotong)"
            await RichParser.edit(status_msg, f"```bash\n{out}\n```")
        except Exception as e:
            await RichParser.edit(status_msg, f"❌ **Error:** `{e}`")
        return

    # Output capture redirection
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    redirected_output = io.StringIO()
    redirected_error = io.StringIO()
    sys.stdout = redirected_output
    sys.stderr = redirected_error

    reply = message.reply_to_message
    from_u = message.from_user
    mention_str = from_u.mention if from_u else "Pengguna"

    # Pre-injected variables agar tidak perlu repot impor manual
    eval_vars = {
        # Core Telegram instances & aliases
        "client": client,
        "bot": client,
        "app": client,
        "c": client,
        "message": message,
        "m": message,
        "msg": message,
        "chat": message.chat,
        "user": from_u,
        "u": from_u,
        "reply": reply,
        "r": reply,
        "mention": mention_str,
        # Helper methods
        "send": client.send_message,
        "reply_text": message.reply_text,
        # Core App Modules & Utilities
        "db": db,
        "Config": Config,
        "config": Config,
        "queue_manager": queue_manager,
        "RichParser": RichParser,
        "clean_markdown": clean_markdown,
        "human_readable_size": human_readable_size,
        "ButtonStyle": ButtonStyle,
        "get_control_panel": get_control_panel,
        "get_control_panel_video": get_control_panel_video,
        "get_start_keyboard": get_start_keyboard,
        "get_help_keyboard": get_help_keyboard,
        # Telegram & Kurigram / Pyrogram Types, Enums & Errors
        "Client": Client,
        "filters": filters,
        "enums": enums if "enums" in globals() else None,
        "types": types if "types" in globals() else None,
        "errors": errors if "errors" in globals() else None,
        "ParseMode": ParseMode,
        "ChatMemberStatus": ChatMemberStatus,
        "ChatType": ChatType if "ChatType" in globals() else None,
        "InlineKeyboardMarkup": InlineKeyboardMarkup,
        "InlineKeyboardButton": InlineKeyboardButton,
        "ReplyParameters": ReplyParameters,
        "LinkPreviewOptions": LinkPreviewOptions,
        "CallbackQuery": CallbackQuery,
        "InputMediaPhoto": InputMediaPhoto,
        "InputMediaVideo": InputMediaVideo,
        "InputMediaAudio": InputMediaAudio,
        "InputMediaDocument": InputMediaDocument,
        # Standard Python Modules
        "asyncio": asyncio,
        "os": os,
        "sys": sys,
        "time": time,
        "datetime": datetime,
        "json": json,
        "shutil": shutil,
        "re": re,
        "math": math,
        "glob": glob,
        "io": io,
        "traceback": traceback,
        "platform": platform,
        "random": random,
        "logging": logging,
        "importlib": importlib,
    }
    # Tambahkan globals modul
    eval_vars.update(globals())
    # Pastikan variabel utama tetap sesuai request aktif
    eval_vars["client"] = client
    eval_vars["bot"] = client
    eval_vars["app"] = client
    eval_vars["message"] = message
    eval_vars["mention"] = mention_str

    try:
        # Eksekusi blok async function
        exec_code = f"async def __ex():\n" + "\n".join(f"    {line}" for line in code.split("\n"))
        try:
            exec(exec_code, eval_vars)
            func = eval_vars["__ex"]
            result = await func()
            if result is not None:
                print(repr(result))
        except Exception:
            # Fallback ke evaluasi single expression
            try:
                result = eval(code, eval_vars)
                if asyncio.iscoroutine(result):
                    result = await result
                if result is not None:
                    print(repr(result))
            except Exception:
                raise

        output = redirected_output.getvalue() + redirected_error.getvalue()
        output = output.strip() or "Eksekusi berhasil (tanpa output return)."
        if len(output) > 3000:
            output = output[:3000] + "... (dipotong)"
        await RichParser.edit(status_msg, f"```python\n{output}\n```")
    except Exception:
        err = traceback.format_exc()
        if len(err) > 3000:
            err = err[:3000] + "..."
        await RichParser.edit(status_msg, f"```python\n{err}\n```")
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
