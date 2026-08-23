# ==============================================================================
#  🇮🇩 Nusantara Stream - Telegram Music & Video Streaming Bot
# ==============================================================================
#  Author   : Amang (@BukanDevelopers)
#  GitHub   : https://github.com/amanqs
#  Project  : Nusantara Stream Telegram Bot
#  License  : GNU General Public License v3.0
# ==============================================================================

"""Kurigram Native Rich Message Helper.

Passes text DIRECTLY to Telegram's own parser via InputRichMessage(markdown=text).
Zero manual conversion — Telegram renders everything.

Reference:
  https://docs.kurigram.icu/api/types/InputRichMessage/
  https://docs.kurigram.icu/api/methods/send_rich_message/
  https://core.telegram.org/bots/api#rich-message-formatting-options
"""
import logging
from typing import Optional, Union

try:
    from kurigram.enums import ParseMode
    from kurigram.types import InputRichMessage, ReplyParameters
    from kurigram.errors import MessageNotModified
except ImportError:
    try:
        from pyrogram.enums import ParseMode
        from pyrogram.types import InputRichMessage, ReplyParameters
        from pyrogram.errors import MessageNotModified
    except ImportError:
        class ParseMode:
            MARKDOWN = "markdown"
            HTML = "html"

        class InputRichMessage:
            def __init__(self, markdown: str = "", html: str = "", **kwargs):
                self.markdown = markdown
                self.html = html

        class ReplyParameters:
            def __init__(self, message_id: int, **kwargs):
                self.message_id = message_id

        class MessageNotModified(Exception):
            pass

logger = logging.getLogger("NusantaraStream.RichParser")


class RichParser:
    """Kurigram Native Rich Message Helper.

    Principle: pass text 100% raw to InputRichMessage(markdown=text).
    Telegram's own built-in parser handles ALL formatting.
    No manual regex conversion whatsoever.
    """

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_input_rich_message(text: str) -> InputRichMessage:
        """Return an InputRichMessage using Telegram's native markdown parser."""
        from core.security import check_system_integrity
        if not check_system_integrity():
            raise RuntimeError("System integrity breached.")
        return InputRichMessage(markdown=str(text) if text else "")

    @staticmethod
    def _filter_rich_kwargs(kwargs: dict) -> dict:
        """Keep only kwargs accepted by send_rich_message()."""
        allowed = {
            "disable_notification",
            "message_thread_id",
            "direct_messages_topic_id",
            "receiver_user_id",
            "callback_query_id",
            "effect_id",
            "reply_parameters",
            "protect_content",
            "allow_paid_broadcast",
            "suggested_post_parameters",
            "reply_markup",
        }
        return {k: v for k, v in kwargs.items() if k in allowed and v is not None}

    # ------------------------------------------------------------------ #
    #  Public API                                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    async def send(client, chat_id, text: str, **kwargs):
        """Send a rich text message via send_rich_message()."""
        reply_markup = kwargs.get("reply_markup", None)
        rich_kwargs = RichParser._filter_rich_kwargs(kwargs)
        if reply_markup is not None and "reply_markup" not in rich_kwargs:
            rich_kwargs["reply_markup"] = reply_markup

        if hasattr(client, "send_rich_message"):
            try:
                return await client.send_rich_message(
                    chat_id=chat_id,
                    rich_message=RichParser.get_input_rich_message(text),
                    **rich_kwargs,
                )
            except Exception as e:
                logger.debug(f"send_rich_message fallback to send_message: {e}")

        kwargs.setdefault("parse_mode", ParseMode.MARKDOWN)
        return await client.send_message(chat_id=chat_id, text=str(text), **kwargs)

    @staticmethod
    async def reply(message, text: str, **kwargs):
        """Reply to a message with rich text via send_rich_message()."""
        quote = kwargs.pop("quote", None)
        reply_markup = kwargs.get("reply_markup", None)

        if quote is not False and "reply_parameters" not in kwargs:
            kwargs["reply_parameters"] = ReplyParameters(message_id=message.id)

        client = getattr(message, "_client", getattr(message, "client", None))
        rich_kwargs = RichParser._filter_rich_kwargs(kwargs)
        if reply_markup is not None and "reply_markup" not in rich_kwargs:
            rich_kwargs["reply_markup"] = reply_markup

        if client and hasattr(client, "send_rich_message"):
            try:
                return await client.send_rich_message(
                    chat_id=message.chat.id,
                    rich_message=RichParser.get_input_rich_message(text),
                    **rich_kwargs,
                )
            except Exception as e:
                logger.debug(f"send_rich_message reply fallback: {e}")

        kwargs.setdefault("parse_mode", ParseMode.MARKDOWN)
        if hasattr(message, "reply_text"):
            return await message.reply_text(str(text), **kwargs)
        if client:
            return await client.send_message(chat_id=message.chat.id, text=str(text), **kwargs)

    @staticmethod
    async def send_photo(client, chat_id, photo, caption: str = "", **kwargs):
        """Send a photo."""
        kwargs.setdefault("parse_mode", ParseMode.MARKDOWN)
        return await client.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=str(caption) if caption else "",
            **kwargs,
        )

    @staticmethod
    async def send_video(client, chat_id, video, caption: str = "", **kwargs):
        """Send a video."""
        kwargs.setdefault("parse_mode", ParseMode.MARKDOWN)
        return await client.send_video(
            chat_id=chat_id,
            video=video,
            caption=str(caption) if caption else "",
            **kwargs,
        )

    @staticmethod
    async def reply_photo(message, photo, caption: str = "", **kwargs):
        """Reply with a photo."""
        kwargs.setdefault("parse_mode", ParseMode.MARKDOWN)
        return await message.reply_photo(
            photo,
            caption=str(caption) if caption else "",
            **kwargs,
        )

    @staticmethod
    async def reply_video(message, video, caption: str = "", **kwargs):
        """Reply with a video."""
        kwargs.setdefault("parse_mode", ParseMode.MARKDOWN)
        return await message.reply_video(
            video,
            caption=str(caption) if caption else "",
            **kwargs,
        )

    @staticmethod
    async def edit(target, text: str, **kwargs):
        """Edit a message using InputRichMessage (Telegram's native markdown parser)."""
        if hasattr(target, "message") and target.message:
            target = target.message

        client = getattr(target, "_client", getattr(target, "client", None))

        kwargs.pop("parse_mode", None)
        kwargs.pop("text", None)
        kwargs.pop("disable_web_page_preview", None)
        kwargs.pop("link_preview_options", None)

        try:
            if client and hasattr(client, "edit_message_text"):
                try:
                    return await client.edit_message_text(
                        chat_id=target.chat.id,
                        message_id=target.id,
                        rich_message=RichParser.get_input_rich_message(text),
                        **kwargs,
                    )
                except MessageNotModified:
                    return target
                except Exception as e:
                    logger.debug(f"edit_message_text rich_message fallback: {e}")

            if hasattr(target, "edit_text"):
                return await target.edit_text(
                    text=str(text),
                    parse_mode=ParseMode.MARKDOWN,
                    **kwargs,
                )
        except MessageNotModified:
            return target
        except Exception as e:
            logger.debug(f"RichParser.edit error: {e}")
            return target
