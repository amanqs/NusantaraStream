# ==============================================================================
#  🇮🇩 Nusantara Stream - Telegram Music & Video Streaming Bot
# ==============================================================================
#  Author   : Amang (@BukanDevelopers)
#  GitHub   : https://github.com/amanqs
#  Project  : Nusantara Stream Telegram Bot
#  License  : GNU General Public License v3.0
# ==============================================================================

from functools import wraps
from typing import Callable, Any
import logging

try:
    from kurigram import filters
    from kurigram.types import Message, CallbackQuery
    from kurigram.enums import ChatMemberStatus, ChatType
    from kurigram.handlers import (
        MessageHandler,
        CallbackQueryHandler,
        ChatMemberUpdatedHandler,
        InlineQueryHandler,
        EditedMessageHandler,
        DeletedMessagesHandler,
        RawUpdateHandler,
    )
except ImportError:
    try:
        from pyrogram import filters
        from pyrogram.types import Message, CallbackQuery
        from pyrogram.enums import ChatMemberStatus, ChatType
        from pyrogram.handlers import (
            MessageHandler,
            CallbackQueryHandler,
            ChatMemberUpdatedHandler,
            InlineQueryHandler,
            EditedMessageHandler,
            DeletedMessagesHandler,
            RawUpdateHandler,
        )
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

        class MessageHandler:
            def __init__(self, callback, filters=None):
                self.callback = callback
                self.filters = filters

        class CallbackQueryHandler:
            def __init__(self, callback, filters=None):
                self.callback = callback
                self.filters = filters

        class ChatMemberUpdatedHandler:
            def __init__(self, callback, filters=None):
                self.callback = callback
                self.filters = filters

        class InlineQueryHandler:
            def __init__(self, callback, filters=None):
                self.callback = callback
                self.filters = filters

        class EditedMessageHandler:
            def __init__(self, callback, filters=None):
                self.callback = callback
                self.filters = filters

        class DeletedMessagesHandler:
            def __init__(self, callback, filters=None):
                self.callback = callback
                self.filters = filters

        class RawUpdateHandler:
            def __init__(self, callback):
                self.callback = callback

from config import Config
from utils.rich_parser import RichParser

logger = logging.getLogger("NusantaraStream.Decorators")

# Registry global untuk handler userbot
USERBOT_HANDLERS: list[tuple[Any, int]] = []


def _resolve_message_filters(*args, **kwargs):
    """Mengubah string/list command seperti @BOT('gban') menjadi filter Pyrogram yang valid."""
    group = kwargs.pop("group", 0)
    prefixes = kwargs.pop("prefixes", None)
    no_forward = kwargs.pop("no_forward", True)
    custom_filters = kwargs.pop("filters", None)

    if not args and custom_filters is None:
        return None, group

    # Jika pemanggilan single arg berupa objek filter Pyrogram
    if len(args) == 1 and not isinstance(args[0], (str, list, tuple, set)):
        return args[0], group

    commands = []
    other_filters = []
    for arg in args:
        if isinstance(arg, str):
            commands.append(arg)
        elif isinstance(arg, (list, tuple, set)):
            commands.extend([str(x) for x in arg])
        else:
            other_filters.append(arg)

    if custom_filters is not None:
        if isinstance(custom_filters, str):
            commands.append(custom_filters)
        elif isinstance(custom_filters, (list, tuple, set)):
            commands.extend([str(x) for x in custom_filters])
        else:
            other_filters.append(custom_filters)

    if commands:
        try:
            if prefixes is not None:
                cmd_f = filters.command(commands, prefixes=prefixes)
            else:
                cmd_f = filters.command(commands)
            if no_forward and hasattr(filters, "forwarded"):
                cmd_f = cmd_f & ~filters.forwarded
            other_filters.insert(0, cmd_f)
        except Exception:
            pass

    if other_filters:
        final_f = other_filters[0]
        for f in other_filters[1:]:
            final_f = final_f & f
    else:
        final_f = None

    return final_f, group


class BotWrapper:
    """Wrapper decorator untuk mendaftarkan handler event ke Bot Client (@BOT)."""

    def __call__(self, *args, **kwargs):
        """Mendukung berbagai gaya pemanggilan:
        - @BOT("gban")
        - @BOT("gban", "globalban")
        - @BOT(["gban", "globalban"])
        - @BOT(filters.command("play") & ~filters.forwarded)
        - @BOT.on_message("gban")
        """
        return self.on_message(*args, **kwargs)

    @staticmethod
    def on_message(*args, **kwargs):
        """Decorator untuk menangani pesan masuk pada bot (@BOT atau @BOT.on_message)."""
        resolved_filter, group = _resolve_message_filters(*args, **kwargs)

        def decorator(func: Callable) -> Callable:
            if not hasattr(func, "handlers"):
                func.handlers = []
            func.handlers.append((MessageHandler(func, resolved_filter), group))
            try:
                from core.bot import bot_client
                if getattr(bot_client, "is_connected", False):
                    bot_client.add_handler(MessageHandler(func, resolved_filter), group)
            except Exception:
                pass
            return func
        return decorator

    @staticmethod
    def on_callback_query(filters=None, group: int = 0):
        """Decorator untuk menangani inline callback query pada bot."""
        def decorator(func: Callable) -> Callable:
            if not hasattr(func, "handlers"):
                func.handlers = []
            func.handlers.append((CallbackQueryHandler(func, filters), group))
            try:
                from core.bot import bot_client
                if getattr(bot_client, "is_connected", False):
                    bot_client.add_handler(CallbackQueryHandler(func, filters), group)
            except Exception:
                pass
            return func
        return decorator

    @staticmethod
    def on_chat_member_updated(filters=None, group: int = 0):
        """Decorator untuk menangani perubahan status member chat pada bot."""
        def decorator(func: Callable) -> Callable:
            if not hasattr(func, "handlers"):
                func.handlers = []
            func.handlers.append((ChatMemberUpdatedHandler(func, filters), group))
            try:
                from core.bot import bot_client
                if getattr(bot_client, "is_connected", False):
                    bot_client.add_handler(ChatMemberUpdatedHandler(func, filters), group)
            except Exception:
                pass
            return func
        return decorator

    @staticmethod
    def on_inline_query(filters=None, group: int = 0):
        """Decorator untuk menangani inline query pada bot."""
        def decorator(func: Callable) -> Callable:
            if not hasattr(func, "handlers"):
                func.handlers = []
            func.handlers.append((InlineQueryHandler(func, filters), group))
            try:
                from core.bot import bot_client
                if getattr(bot_client, "is_connected", False):
                    bot_client.add_handler(InlineQueryHandler(func, filters), group)
            except Exception:
                pass
            return func
        return decorator

    @staticmethod
    def on_edited_message(*args, **kwargs):
        """Decorator untuk menangani pesan yang diedit pada bot."""
        resolved_filter, group = _resolve_message_filters(*args, **kwargs)

        def decorator(func: Callable) -> Callable:
            if not hasattr(func, "handlers"):
                func.handlers = []
            func.handlers.append((EditedMessageHandler(func, resolved_filter), group))
            try:
                from core.bot import bot_client
                if getattr(bot_client, "is_connected", False):
                    bot_client.add_handler(EditedMessageHandler(func, resolved_filter), group)
            except Exception:
                pass
            return func
        return decorator

    @staticmethod
    def on_deleted_messages(filters=None, group: int = 0):
        """Decorator untuk menangani pesan yang dihapus pada bot."""
        def decorator(func: Callable) -> Callable:
            if not hasattr(func, "handlers"):
                func.handlers = []
            func.handlers.append((DeletedMessagesHandler(func, filters), group))
            try:
                from core.bot import bot_client
                if getattr(bot_client, "is_connected", False):
                    bot_client.add_handler(DeletedMessagesHandler(func, filters), group)
            except Exception:
                pass
            return func
        return decorator

    @staticmethod
    def on_raw_update(group: int = 0):
        """Decorator untuk menangani raw update MTProto pada bot."""
        def decorator(func: Callable) -> Callable:
            if not hasattr(func, "handlers"):
                func.handlers = []
            func.handlers.append((RawUpdateHandler(func), group))
            try:
                from core.bot import bot_client
                if getattr(bot_client, "is_connected", False):
                    bot_client.add_handler(RawUpdateHandler(func), group)
            except Exception:
                pass
            return func
        return decorator


class UserbotWrapper:
    """Wrapper decorator untuk mendaftarkan handler event ke Userbot Assistant (@USER)."""

    def __call__(self, *args, **kwargs):
        """Mendukung berbagai gaya pemanggilan:
        - @USER("ping")
        - @USER("ping", "userping")
        - @USER(["ping", "userping"])
        - @USER(filters.command("ping"))
        - @USER.on_message("ping")
        """
        return self.on_message(*args, **kwargs)

    @staticmethod
    def on_message(*args, **kwargs):
        """Decorator untuk menangani pesan masuk pada akun Userbot/Asisten (@USER atau @USER.on_message)."""
        resolved_filter, group = _resolve_message_filters(*args, **kwargs)

        def decorator(func: Callable) -> Callable:
            handler_tuple = (MessageHandler(func, resolved_filter), group)
            if not hasattr(func, "userbot_handlers"):
                func.userbot_handlers = []
            func.userbot_handlers.append(handler_tuple)
            if handler_tuple not in USERBOT_HANDLERS:
                USERBOT_HANDLERS.append(handler_tuple)
            try:
                from core.userbot import userbot_client
                if getattr(userbot_client, "is_connected", False):
                    userbot_client.add_handler(MessageHandler(func, resolved_filter), group)
            except Exception:
                pass
            return func
        return decorator

    @staticmethod
    def on_edited_message(*args, **kwargs):
        """Decorator untuk menangani pesan yang diedit pada userbot."""
        resolved_filter, group = _resolve_message_filters(*args, **kwargs)

        def decorator(func: Callable) -> Callable:
            handler_tuple = (EditedMessageHandler(func, resolved_filter), group)
            if not hasattr(func, "userbot_handlers"):
                func.userbot_handlers = []
            func.userbot_handlers.append(handler_tuple)
            if handler_tuple not in USERBOT_HANDLERS:
                USERBOT_HANDLERS.append(handler_tuple)
            try:
                from core.userbot import userbot_client
                if getattr(userbot_client, "is_connected", False):
                    userbot_client.add_handler(EditedMessageHandler(func, resolved_filter), group)
            except Exception:
                pass
            return func
        return decorator

    @staticmethod
    def on_callback_query(filters=None, group: int = 0):
        """Decorator untuk menangani callback query pada userbot."""
        def decorator(func: Callable) -> Callable:
            handler_tuple = (CallbackQueryHandler(func, filters), group)
            if not hasattr(func, "userbot_handlers"):
                func.userbot_handlers = []
            func.userbot_handlers.append(handler_tuple)
            if handler_tuple not in USERBOT_HANDLERS:
                USERBOT_HANDLERS.append(handler_tuple)
            try:
                from core.userbot import userbot_client
                if getattr(userbot_client, "is_connected", False):
                    userbot_client.add_handler(CallbackQueryHandler(func, filters), group)
            except Exception:
                pass
            return func
        return decorator

    @staticmethod
    def on_chat_member_updated(filters=None, group: int = 0):
        """Decorator untuk menangani update member chat pada userbot."""
        def decorator(func: Callable) -> Callable:
            handler_tuple = (ChatMemberUpdatedHandler(func, filters), group)
            if not hasattr(func, "userbot_handlers"):
                func.userbot_handlers = []
            func.userbot_handlers.append(handler_tuple)
            if handler_tuple not in USERBOT_HANDLERS:
                USERBOT_HANDLERS.append(handler_tuple)
            try:
                from core.userbot import userbot_client
                if getattr(userbot_client, "is_connected", False):
                    userbot_client.add_handler(ChatMemberUpdatedHandler(func, filters), group)
            except Exception:
                pass
            return func
        return decorator

    @staticmethod
    def on_raw_update(group: int = 0):
        """Decorator untuk menangani raw update MTProto pada userbot."""
        def decorator(func: Callable) -> Callable:
            handler_tuple = (RawUpdateHandler(func), group)
            if not hasattr(func, "userbot_handlers"):
                func.userbot_handlers = []
            func.userbot_handlers.append(handler_tuple)
            if handler_tuple not in USERBOT_HANDLERS:
                USERBOT_HANDLERS.append(handler_tuple)
            try:
                from core.userbot import userbot_client
                if getattr(userbot_client, "is_connected", False):
                    userbot_client.add_handler(RawUpdateHandler(func), group)
            except Exception:
                pass
            return func
        return decorator



BOT = BotWrapper()
USER = UserbotWrapper()

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

        from utils.database import db
        if db.is_user_gbanned(user.id):
            if is_callback:
                return await update.answer("❌ Anda telah di-banned secara global.", show_alert=True)
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
