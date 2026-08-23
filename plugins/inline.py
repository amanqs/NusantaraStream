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
    from kurigram import Client
    from kurigram.types import (
        InlineQuery,
        InlineQueryResultArticle,
        InputTextMessageContent,
        InlineKeyboardMarkup,
        InlineKeyboardButton,
    )
    from kurigram.enums import ParseMode
except ImportError:
    from pyrogram import Client
    from pyrogram.types import (
        InlineQuery,
        InlineQueryResultArticle,
        InputTextMessageContent,
        InlineKeyboardMarkup,
        InlineKeyboardButton,
    )
    from pyrogram.enums import ParseMode

from config import Config
from utils.formatters import clean_markdown, get_readable_time, get_clean_youtube_thumbnail
from utils.ytdl import ytdl_helper

logger = logging.getLogger("NusantaraStream.Inline")


@Client.on_inline_query()
async def inline_search_handler(client: Client, inline_query: InlineQuery):
    """Handler pencarian inline YouTube (@BotUsername <judul lagu>)."""
    query_text = inline_query.query.strip()
    bot_username = getattr(client, "me", None)
    bot_user = bot_username.username if bot_username else Config.BOT_USERNAME

    # 1. Jika query kosong atau sangat pendek, tampilkan panduan & menu bantuan inline
    if not query_text:
        help_text = (
            f"🔍 **Pencarian Inline {Config.BOT_NAME}**\n\n"
            f"> Ketik `@{bot_user} [judul lagu]` di chat mana saja untuk mencari dan membagikan lagu!\n\n"
            f"**Contoh Penggunaan:**\n"
            f"> 🎵 **Cari Lagu:** `@{bot_user} Indonesia Raya`\n"
            f"> 🎬 **Cari Video:** `@{bot_user} Cinematic 4K`\n\n"
            f"🤖 *Nusantara Stream Bot*"
        )
        help_article = InlineQueryResultArticle(
            title="🔍 Cari Musik & Video di YouTube",
            description="Ketik judul lagu atau nama artis setelah mention bot.",
            input_message_content=InputTextMessageContent(
                help_text,
                parse_mode=ParseMode.MARKDOWN
            ),
            thumb_url="https://telegra.ph/file/0c9a0c71a337191cd10c4.jpg",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔍 Mulai Cari Lagu",
                            switch_inline_query_current_chat="",
                        ),
                        InlineKeyboardButton(
                            "➕ Tambah ke Grup",
                            url=f"https://t.me/{bot_user}?startgroup=true",
                        ),
                    ]
                ]
            ),
        )

        radio_text = (
            f"📻 **Stasiun Radio Indonesia 24/7**\n\n"
            f"> Dengarkan siaran radio favorit langsung di Voice Chat grup Anda!\n\n"
            f"🤖 *Nusantara Stream Bot*"
        )
        radio_article = InlineQueryResultArticle(
            title="📻 Stasiun Radio Indonesia 24/7",
            description="Dengarkan siaran Prambors, GenFM, Hard Rock FM di Voice Chat.",
            input_message_content=InputTextMessageContent(
                radio_text,
                parse_mode=ParseMode.MARKDOWN
            ),
            thumb_url="https://telegra.ph/file/0c9a0c71a337191cd10c4.jpg",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "📻 Buka Pemutar Radio",
                            url=f"https://t.me/{bot_user}?start=help_radio",
                        )
                    ]
                ]
            ),
        )

        return await inline_query.answer(
            results=[help_article, radio_article],
            cache_time=5,
            is_personal=True,
        )

    # 2. Cari hasil di YouTube via ytdl_helper
    try:
        results = await ytdl_helper.search_youtube(query_text, limit=10)
    except Exception as e:
        logger.error(f"Error pada inline search: {e}")
        results = []

    if not results:
        not_found_text = (
            f"❌ **Hasil Pencarian Tidak Ditemukan**\n\n"
            f"> Kata kunci: `{clean_markdown(query_text)}`"
        )
        not_found_article = InlineQueryResultArticle(
            title="❌ Tidak Ada Hasil",
            description=f"Tidak ditemukan hasil pencarian untuk: '{query_text}'",
            input_message_content=InputTextMessageContent(
                not_found_text,
                parse_mode=ParseMode.MARKDOWN
            ),
        )
        return await inline_query.answer(
            results=[not_found_article],
            cache_time=5,
            is_personal=True,
        )

    # 3. Format hasil pencarian ke dalam InlineQueryResultArticle dengan Blockquote Native
    inline_results = []
    for item in results:
        vid_id = item.get("id")
        if not vid_id:
            continue

        raw_title = item.get("title", "Tidak Diketahui")
        title = clean_markdown(raw_title)
        channel = clean_markdown(item.get("channel") or "YouTube")
        duration = item.get("duration_string") or get_readable_time(item.get("duration", 0))
        url = item.get("url", f"https://www.youtube.com/watch?v={vid_id}")
        clean_thumb = get_clean_youtube_thumbnail(url, item.get("thumbnail"))

        photo_preview = f"[\u200b]({clean_thumb})" if clean_thumb else ""

        message_content = (
            f"{photo_preview}🔍 **Hasil Pencarian YouTube**\n\n"
            f"💿 **[{title}]({url})**\n\n"
            f"> 📡 **Channel:** `{channel}`\n"
            f"> ⏱ **Durasi:** `{duration}`\n\n"
            f"🤖 *Nusantara Stream Bot*"
        )

        markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🎵 Putar Audio di Grup",
                        url=f"https://t.me/{bot_user}?startgroup=play_{vid_id}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "🎬 Putar Video di Grup",
                        url=f"https://t.me/{bot_user}?startgroup=vplay_{vid_id}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "📥 Unduh MP3",
                        url=f"https://t.me/{bot_user}?start=song_{vid_id}",
                    ),
                    InlineKeyboardButton(
                        "📺 Buka YouTube",
                        url=url,
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "🔍 Cari Lagu Lain",
                        switch_inline_query_current_chat="",
                    )
                ],
            ]
        )

        article = InlineQueryResultArticle(
            id=vid_id,
            title=raw_title,
            description=f"👤 {item.get('channel', 'YouTube')} • ⏱ {duration}",
            thumb_url=clean_thumb or "https://telegra.ph/file/0c9a0c71a337191cd10c4.jpg",
            input_message_content=InputTextMessageContent(
                message_content,
                parse_mode=ParseMode.MARKDOWN
            ),
            reply_markup=markup,
        )
        inline_results.append(article)

    await inline_query.answer(
        results=inline_results,
        cache_time=15,
        is_personal=True,
    )