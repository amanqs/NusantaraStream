# ==============================================================================
#  🇮🇩 Nusantara Stream - Telegram Music & Video Streaming Bot
# ==============================================================================
#  Author   : Amang (@BukanDevelopers)
#  GitHub   : https://github.com/amanqs
#  Project  : Nusantara Stream Telegram Bot
#  License  : GNU General Public License v3.0
# ==============================================================================

from functools import wraps
from typing import Callable
import logging

try:
    from kurigram.types import Message, CallbackQuery
    from kurigram.enums import ChatMemberStatus, ChatType
except ImportError:
    try:
        from pyrogram.types import Message, CallbackQuery
        from pyrogram.enums import ChatMemberStatus, ChatType
    except ImportError:
        class Message:
            pass

        class CallbackQuery:
            pass

        class ChatMemberStatus:
            OWNER = "creator"
            ADMINISTRATOR = "administrator"
            MEMBER = "member"

        class ChatType:
            PRIVATE = "private"
            GROUP = "group"
            SUPERGROUP = "supergroup"
            CHANNEL = "channel"

from config import Config
from utils.rich_parser import RichParser

logger = logging.getLogger("NusantaraStream.Decorators")

# Chat ID -> set of authorized User IDs
AUTHORIZED_USERS: dict[int, set[int]] = {}


def add_authorized_user(chat_id: int, user_id: int):
    """Menambahkan user ke daftar izin khusus di grup."""
    if chat_id not in AUTHORIZED_USERS:
        AUTHORIZED_USERS[chat_id] = set()
    AUTHORIZED_USERS[chat_id].add(user_id)


def remove_authorized_user(chat_id: int, user_id: int):
    """Menghapus user dari daftar izin khusus."""
    if chat_id in AUTHORIZED_USERS:
        AUTHORIZED_USERS[chat_id].discard(user_id)


def get_authorized_users(chat_id: int) -> set[int]:
    """Mengambil daftar user yang diizinkan di grup."""
    return AUTHORIZED_USERS.get(chat_id, set())


def authorized_only(func: Callable):
    """Decorator untuk memastikan hanya Admin grup, Sudo, atau Authorized User yang dapat mengontrol bot."""

    @wraps(func)
    async def wrapper(client, update: Message | CallbackQuery, *args, **kwargs):
        is_callback = isinstance(update, CallbackQuery)
        user = update.from_user
        chat = update.message.chat if is_callback else update.chat

        if not user:
            return

        # Private Chat: izinkan pemilik bot & sudo
        if chat.type == ChatType.PRIVATE:
            return await func(client, update, *args, **kwargs)

        # Sudo users, Developer & Owner selalu diizinkan
        if Config.is_sudo(user.id) or Config.is_owner(user.id):
            return await func(client, update, *args, **kwargs)

        # Cek apakah user adalah peminta (requester) konten/lagu/film yang sedang diputar
        from utils.queue import queue_manager
        current_track = queue_manager.get_current_track(chat.id)
        if current_track and getattr(current_track, "requested_by_id", 0) == user.id:
            return await func(client, update, *args, **kwargs)

        # Cek apakah user ada dalam daftar khusus grup
        if user.id in get_authorized_users(chat.id):
            return await func(client, update, *args, **kwargs)

        # Cek status admin di grup Telegram
        try:
            member = await chat.get_member(user.id)
            if member.status in (
                ChatMemberStatus.OWNER,
                ChatMemberStatus.ADMINISTRATOR,
            ):
                return await func(client, update, *args, **kwargs)
        except Exception as e:
            logger.debug(f"Error pengecekan status admin: {e}")

        # Tolak akses jika bukan admin
        err_text = "⚠️ *Perintah ini hanya dapat digunakan oleh Admin Grup atau Pengguna Terotorisasi.*"
        if is_callback:
            return await update.answer(
                "❌ Anda bukan admin grup ini!", show_alert=True
            )
        else:
            return await RichParser.reply(update, err_text)

    return wrapper


def bot_admin_check(func: Callable):
    """Decorator untuk memastikan bot memiliki hak admin di grup."""

    @wraps(func)
    async def wrapper(client, message: Message, *args, **kwargs):
        if message.chat.type == ChatType.PRIVATE:
            return await func(client, message, *args, **kwargs)

        try:
            bot_member = await message.chat.get_member(client.id)
            if bot_member.status not in (
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.OWNER,
            ):
                return await RichParser.reply(
                    message,
                    "⚠️ **Perhatian:** Bot harus menjadi **Admin** di grup ini dengan hak kelola Voice Chat agar dapat memutar musik!"
                )
        except Exception as e:
            logger.debug(f"Error get_member bot: {e}")

        return await func(client, message, *args, **kwargs)

    return wrapper
