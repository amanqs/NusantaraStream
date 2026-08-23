# ==============================================================================
#  🇮🇩 Nusantara Stream - Telegram Music & Video Streaming Bot
# ==============================================================================
#  Author   : Amang (@BukanDevelopers)
#  GitHub   : https://github.com/amanqs
#  Project  : Nusantara Stream Telegram Bot
#  License  : GNU General Public License v3.0
# ==============================================================================

import math
import logging
from typing import Optional

try:
    from kurigram import Client, filters
    from kurigram.types import (
        Message,
        CallbackQuery,
        InlineKeyboardMarkup,
        InlineKeyboardButton,
        LinkPreviewOptions,
    )
    from kurigram.enums import ChatType
except ImportError:
    from pyrogram import Client, filters
    from pyrogram.types import (
        Message,
        CallbackQuery,
        InlineKeyboardMarkup,
        InlineKeyboardButton,
        LinkPreviewOptions,
    )
    from pyrogram.enums import ChatType

from config import Config
from utils.database import db
from utils.formatters import clean_markdown, get_readable_time, get_clean_youtube_thumbnail
from utils.keyboards import resolve_style, ButtonStyle
from utils.rich_parser import RichParser
from utils.queue import queue_manager, TrackInfo
from utils.call_manager import call_manager
from utils.ytdl import ytdl_helper
from utils.decorators import bot_admin_check

logger = logging.getLogger("NusantaraStream.Playlist")

PAGE_SIZE = 5


def get_playlist_keyboard(
    user_id: int,
    current_page: int,
    total_pages: int,
    has_tracks: bool,
) -> InlineKeyboardMarkup:
    """Membuat tombol navigasi interaktif untuk daftar playlist."""
    buttons = []

    if has_tracks:
        # Baris 1: Tombol Putar Semua Lagu di Playlist
        buttons.append(
            [
                InlineKeyboardButton(
                    "▶️ Putar Semua Lagu di Playlist",
                    callback_data=f"pl_play:{user_id}",
                    style=ButtonStyle.SUCCESS,
                )
            ]
        )

        # Baris 2: Navigasi Halaman jika lebih dari 1 halaman
        if total_pages > 1:
            nav = []
            if current_page > 1:
                nav.append(
                    InlineKeyboardButton(
                        "⬅️ Sebelumnya",
                        callback_data=f"pl_page:{current_page - 1}:{user_id}",
                        style=ButtonStyle.PRIMARY,
                    )
                )
            nav.append(
                InlineKeyboardButton(
                    f"📄 {current_page}/{total_pages}",
                    callback_data="noop",
                    style=ButtonStyle.DEFAULT,
                )
            )
            if current_page < total_pages:
                nav.append(
                    InlineKeyboardButton(
                        "Berikutnya ➡️",
                        callback_data=f"pl_page:{current_page + 1}:{user_id}",
                        style=ButtonStyle.PRIMARY,
                    )
                )
            buttons.append(nav)

        # Baris 3: Menu Hapus & Bersihkan Playlist
        buttons.append(
            [
                InlineKeyboardButton(
                    "🗑 Hapus Lagu...",
                    callback_data=f"pl_delmenu:{current_page}:{user_id}",
                    style=ButtonStyle.PRIMARY,
                ),
                InlineKeyboardButton(
                    "🧹 Kosongkan Playlist",
                    callback_data=f"pl_clear_confirm:{user_id}",
                    style=ButtonStyle.DANGER,
                ),
            ]
        )

    # Baris Terakhir: Tutup Menu
    buttons.append(
        [
            InlineKeyboardButton(
                "❌ Tutup Menu",
                callback_data="help:close",
                style=ButtonStyle.DANGER,
            )
        ]
    )

    return InlineKeyboardMarkup(buttons)


def format_playlist_card(
    tracks: list[dict],
    user_name: str,
    page: int = 1,
) -> tuple[str, int]:
    """Membuat Table Card daftar playlist pengguna."""
    total_tracks = len(tracks)
    if total_tracks == 0:
        u_name = user_name.replace("|", "-").replace("`", "")
        card = (
            f"| 📂 Playlist Pribadi: {u_name} |\n"
            f"|:---:|\n"
            f"| Playlist Anda saat ini masih kosong |\n\n"
            f"| 💡 Cara Menambah Lagu ke Playlist |\n"
            f"|:---|\n"
            f"| 1. Balas (reply) pesan lagu dengan `/save` |\n"
            f"| 2. Ketik `/save [judul lagu / link]` |\n\n"
            f"| 🤖 Nusantara Stream 🤖 |\n"
            f"|:---:|\n"
            f"| |"
        )
        return card, 1

    total_pages = math.ceil(total_tracks / PAGE_SIZE)
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * PAGE_SIZE
    page_tracks = tracks[start_idx : start_idx + PAGE_SIZE]

    card = (
        f"| 📂 Playlist Pribadi: {user_name} |\n"
        f"|:---:|\n"
        f"| Total: {total_tracks} Lagu Tersimpan (Halaman {page}/{total_pages}) |\n\n"
        f"| No | Judul Lagu | Durasi | Channel |\n"
        f"|:---:|:---|:---:|:---:|\n"
    )

    for i, t in enumerate(page_tracks, start=start_idx + 1):
        clean_title = clean_markdown(t.get("title", "Lagu")[:24]).replace("|", "\\|")
        dur_str = get_readable_time(t.get("duration", 0))
        clean_ch = clean_markdown(t.get("channel", "YouTube")[:16]).replace("|", "\\|")
        url = t.get("url", "https://youtube.com")
        card += f"| #{i} | [{clean_title}]({url}) | `{dur_str}` | {clean_ch} |\n"

    card += (
        f"\n| 💡 Ketik `/delplaylist <nomor>` untuk menghapus lagu tertentu |\n"
        f"|:---:|\n"
        f"| |"
    )

    return card, total_pages


@Client.on_message(filters.command(["save", "saveplaylist", "addplaylist"]) & ~filters.forwarded)
async def save_track_command(client: Client, message: Message):
    """Handler perintah /save untuk menyimpan lagu ke playlist pribadi."""
    user = message.from_user
    if not user:
        return

    # 1. Cek query dari argumen perintah atau reply
    query = ""
    if len(message.command) > 1:
        query = " ".join(message.command[1:])
    elif message.reply_to_message:
        # Ambil dari audio/video telegram yang dibalas
        reply = message.reply_to_message
        if reply.audio:
            query = reply.audio.title or reply.audio.file_name or "Audio Telegram"
        elif reply.video:
            query = reply.video.file_name or "Video Telegram"
        elif reply.text:
            query = reply.text
    else:
        # Cek lagu yang sedang diputar di grup saat ini
        if message.chat.type.value in ("group", "supergroup"):
            curr = queue_manager.get_current_track(message.chat.id)
            if curr:
                query = curr.url or curr.title

    if not query:
        return await RichParser.reply(
            message,
            "ℹ️ **Cara Menyimpan Lagu ke Playlist:**\n"
            "> - Ketik `/save [judul lagu / link YouTube]`\n"
            "> - Balas pesan audio di grup dengan `/save`\n"
            "> - Ketik `/save` saat ada lagu yang sedang diputar di grup",
        )

    status_msg = await RichParser.reply(message, "🔍 *Mencari informasi lagu untuk disimpan...*")

    # Ambil detail lagu dari YouTube
    try:
        track_info = await ytdl_helper.extract_track_info(query)
    except Exception as e:
        return await RichParser.edit(status_msg, f"❌ **Gagal menemukan lagu:** `{clean_markdown(str(e))}`")

    if not track_info:
        return await RichParser.edit(status_msg, "❌ **Lagu tidak ditemukan di YouTube.**")

    # Simpan ke database
    success, note = await db.add_to_playlist(user.id, track_info)
    if not success:
        return await RichParser.edit(status_msg, f"⚠️ *{note}*")

    t_title = clean_markdown(track_info.get("title", "Lagu")).replace("|", "\\|")
    t_chan = clean_markdown(track_info.get("channel", "YouTube")).replace("|", "\\|")
    t_dur = get_readable_time(track_info.get("duration", 0))

    card = (
        "| ✅ Lagu Berhasil Disimpan ke Playlist |\n"
        "|:---:|\n"
        f"| Tersimpan di playlist milik {clean_markdown(user.first_name)} |\n\n"
        "| Parameter | Detail Informasi |\n"
        "|:---|:---|\n"
        f"| 💿 Judul Lagu | [{t_title}]({track_info.get('url')}) |\n"
        f"| ⏱ Durasi | `{t_dur}` |\n"
        f"| 📡 Channel | {t_chan} |\n\n"
        "| 💡 Ketik `/playlist` untuk melihat seluruh lagu Anda |\n"
        "|:---:|\n"
        "| |"
    )

    markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📂 Buka Playlist Saya",
                    callback_data=f"pl_page:1:{user.id}",
                    style=ButtonStyle.PRIMARY,
                ),
                InlineKeyboardButton(
                    "🗑 Tutup",
                    callback_data="help:close",
                    style=ButtonStyle.DANGER,
                ),
            ]
        ]
    )

    await RichParser.edit(status_msg, card, reply_markup=markup)


@Client.on_message(filters.command(["playlist", "myplaylist", "daftarlagu"]) & ~filters.forwarded)
async def view_playlist_command(client: Client, message: Message):
    """Handler perintah /playlist untuk melihat daftar lagu tersimpan."""
    user = message.from_user
    if not user:
        return

    user_name = clean_markdown(user.first_name).replace("|", "\\|")
    tracks = await db.get_playlist(user.id)

    card, total_pages = format_playlist_card(tracks, user_name, page=1)
    markup = get_playlist_keyboard(
        user_id=user.id,
        current_page=1,
        total_pages=total_pages,
        has_tracks=len(tracks) > 0,
    )

    await RichParser.reply(
        message,
        card,
        reply_markup=markup,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@Client.on_message(filters.command(["playplaylist", "playpl", "putarplaylist"]) & ~filters.forwarded)
@bot_admin_check
async def play_playlist_command(client: Client, message: Message):
    """Handler perintah /playplaylist untuk memutar seluruh lagu playlist di Voice Chat."""
    chat = message.chat
    user = message.from_user
    if not user:
        return

    if chat.type == ChatType.PRIVATE:
        return await RichParser.reply(
            message,
            "⚠️ *Perintah ini hanya dapat digunakan di obrolan grup atau Voice Chat.*",
        )

    tracks = await db.get_playlist(user.id)
    if not tracks:
        return await RichParser.reply(
            message,
            "⚠️ *Playlist Anda masih kosong.*\n"
            "> Gunakan `/save [judul lagu]` untuk menambahkan lagu ke playlist Anda terlebih dahulu.",
        )

    status_msg = await RichParser.reply(
        message,
        f"⚡ *Memuat {len(tracks)} lagu dari playlist {clean_markdown(user.first_name)} ke antrean...*",
    )

    chat_id = chat.id
    user_name = clean_markdown(user.first_name)
    user_id = user.id

    added_count = 0
    first_track_info = None

    for t in tracks:
        track = TrackInfo(
            title=t.get("title", "Lagu Playlist"),
            url=t.get("url", ""),
            stream_url=t.get("url", ""),
            duration=int(t.get("duration", 0)),
            channel=t.get("channel", "YouTube"),
            requested_by_id=user_id,
            requested_by_name=user_name,
            thumbnail=t.get("thumbnail", ""),
            is_video=False,
        )
        if not first_track_info and not queue_manager.is_playing(chat_id):
            first_track_info = track
        else:
            queue_manager.add_track(chat_id, track)
        added_count += 1

    # Jika belum ada yang diputar, mulai lagu pertama
    if first_track_info:
        try:
            await call_manager.play_stream(chat_id, first_track_info)
            queue_manager.set_current_track(chat_id, first_track_info)
        except Exception as e:
            logger.error(f"Gagal memutar playlist di VC: {e}")
            return await RichParser.edit(
                status_msg,
                f"❌ **Gagal memulai pemutaran di Voice Chat:** `{clean_markdown(str(e))}`",
            )

    card = (
        "| 📂 Playlist Dimasukkan ke Antrean |\n"
        "|:---:|\n"
        f"| Playlist milik {clean_markdown(user.first_name)} siap diputar |\n\n"
        "| Parameter | Nilai |\n"
        "|:---|:---|\n"
        f"| 🎵 Jumlah Lagu | `{added_count} lagu` |\n"
        f"| 📜 Antrean Total | `{queue_manager.get_queue_length(chat_id)} lagu` |\n"
        f"| 👤 Diminta oleh | [{user_name}](tg://user?id={user_id}) |\n\n"
        "| 🤖 Nusantara Stream 🤖 |\n"
        "|:---:|\n"
        "| |"
    )

    markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📜 Lihat Antrean Aktif",
                    callback_data=f"ctrl:queue:1:{chat_id}",
                    style=ButtonStyle.PRIMARY,
                ),
                InlineKeyboardButton(
                    "🎛 Control Panel",
                    callback_data=f"ctrl:player:{chat_id}",
                    style=ButtonStyle.SUCCESS,
                ),
            ]
        ]
    )

    await RichParser.edit(status_msg, card, reply_markup=markup)


@Client.on_message(filters.command(["delplaylist", "delpl", "hapuslagu"]) & ~filters.forwarded)
async def delete_playlist_item_command(client: Client, message: Message):
    """Handler perintah /delplaylist <nomor urut> untuk menghapus lagu dari playlist."""
    user = message.from_user
    if not user:
        return

    if len(message.command) < 2 or not message.command[1].isdigit():
        return await RichParser.reply(
            message,
            "ℹ️ **Format Perintah Hapus:**\n"
            "> Ketik `/delplaylist <nomor>` (contoh: `/delplaylist 2`)\n\n"
            "*Cek nomor lagu Anda melalui perintah `/playlist`*",
        )

    idx = int(message.command[1])
    success, result = await db.remove_from_playlist(user.id, idx)
    if not success:
        return await RichParser.reply(message, f"❌ *{result}*")

    card = (
        "| 🗑 Lagu Berhasil Dihapus dari Playlist |\n"
        "|:---:|\n"
        f"| Lagu #{idx} telah dihapus |\n\n"
        "| Parameter | Nilai |\n"
        "|:---|:---|\n"
        f"| 💿 Judul Lagu | {clean_markdown(result)} |\n"
        f"| 👤 Pemilik | {clean_markdown(user.first_name)} |\n\n"
        "| 🤖 Nusantara Stream 🤖 |\n"
        "|:---:|\n"
        "| |"
    )

    markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📂 Buka Playlist",
                    callback_data=f"pl_page:1:{user.id}",
                    style=ButtonStyle.PRIMARY,
                ),
                InlineKeyboardButton(
                    "🗑 Tutup",
                    callback_data="help:close",
                    style=ButtonStyle.DANGER,
                ),
            ]
        ]
    )

    await RichParser.reply(message, card, reply_markup=markup)


# ------------------------------------------------------------------ #
#  Callback Handlers untuk Navigasi & Aksi Playlist                  #
# ------------------------------------------------------------------ #


@Client.on_callback_query(filters.regex(r"^pl_page:(\d+):(\d+)"))
async def playlist_page_callback(client: Client, query: CallbackQuery):
    """Handler navigasi halaman playlist via callback button."""
    data = query.data.split(":")
    page = int(data[1])
    target_user_id = int(data[2])

    if query.from_user and query.from_user.id != target_user_id:
        return await query.answer("⚠️ Anda hanya dapat melihat playlist milik Anda sendiri.", show_alert=True)

    user_name = clean_markdown(query.from_user.first_name).replace("|", "\\|")
    tracks = await db.get_playlist(target_user_id)

    card, total_pages = format_playlist_card(tracks, user_name, page=page)
    markup = get_playlist_keyboard(
        user_id=target_user_id,
        current_page=page,
        total_pages=total_pages,
        has_tracks=len(tracks) > 0,
    )

    try:
        await RichParser.edit(
            query,
            card,
            reply_markup=markup,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
    except Exception:
        pass
    await query.answer()


@Client.on_callback_query(filters.regex(r"^pl_play:(\d+)"))
async def playlist_play_callback(client: Client, query: CallbackQuery):
    """Handler callback tombol 'Putar Semua Lagu di Playlist'."""
    target_user_id = int(query.data.split(":")[1])
    chat = query.message.chat

    if chat.type == ChatType.PRIVATE:
        return await query.answer(
            "⚠️ Fitur ini hanya dapat diputar di grup yang memiliki Voice Chat aktif.",
            show_alert=True,
        )

    tracks = await db.get_playlist(target_user_id)
    if not tracks:
        return await query.answer("Playlist Anda kosong.", show_alert=True)

    await query.answer(f"Memulai {len(tracks)} lagu dari playlist...")

    chat_id = chat.id
    user_name = clean_markdown(query.from_user.first_name if query.from_user else "Pengguna")
    user_id = query.from_user.id if query.from_user else 0

    added_count = 0
    first_track_info = None

    for t in tracks:
        track = TrackInfo(
            title=t.get("title", "Lagu Playlist"),
            url=t.get("url", ""),
            stream_url=t.get("url", ""),
            duration=int(t.get("duration", 0)),
            channel=t.get("channel", "YouTube"),
            requested_by_id=user_id,
            requested_by_name=user_name,
            thumbnail=t.get("thumbnail", ""),
            is_video=False,
        )
        if not first_track_info and not queue_manager.is_playing(chat_id):
            first_track_info = track
        else:
            queue_manager.add_track(chat_id, track)
        added_count += 1

    if first_track_info:
        try:
            await call_manager.play_stream(chat_id, first_track_info)
            queue_manager.set_current_track(chat_id, first_track_info)
        except Exception as e:
            logger.error(f"Gagal memutar playlist: {e}")

    card = (
        "| 📂 Playlist Dimasukkan ke Antrean |\n"
        "|:---:|\n"
        f"| {added_count} lagu dari playlist {user_name} siap diputar |\n\n"
        "| Parameter | Nilai |\n"
        "|:---|:---|\n"
        f"| 🎵 Jumlah Lagu | `{added_count} lagu` |\n"
        f"| 📜 Antrean Total | `{queue_manager.get_queue_length(chat_id)} lagu` |\n"
        f"| 👤 Diminta oleh | [{user_name}](tg://user?id={user_id}) |\n\n"
        "| 🤖 Nusantara Stream 🤖 |\n"
        "|:---:|\n"
        "| |"
    )

    markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📜 Antrean Aktif",
                    callback_data=f"ctrl:queue:1:{chat_id}",
                    style=ButtonStyle.PRIMARY,
                ),
                InlineKeyboardButton(
                    "🎛 Control Panel",
                    callback_data=f"ctrl:player:{chat_id}",
                    style=ButtonStyle.SUCCESS,
                ),
            ]
        ]
    )

    await RichParser.edit(query, card, reply_markup=markup)


@Client.on_callback_query(filters.regex(r"^pl_delmenu:(\d+):(\d+)"))
async def playlist_delmenu_callback(client: Client, query: CallbackQuery):
    """Handler menu tombol cepat untuk menghapus lagu dari halaman aktif."""
    data = query.data.split(":")
    page = int(data[1])
    target_user_id = int(data[2])

    if query.from_user and query.from_user.id != target_user_id:
        return await query.answer("⚠️ Anda hanya dapat mengubah playlist Anda sendiri.", show_alert=True)

    tracks = await db.get_playlist(target_user_id)
    if not tracks:
        return await query.answer("Playlist Anda kosong.", show_alert=True)

    start_idx = (page - 1) * PAGE_SIZE
    page_tracks = tracks[start_idx : start_idx + PAGE_SIZE]

    buttons = []
    for i, t in enumerate(page_tracks, start=start_idx + 1):
        t_name = t.get("title", f"Lagu #{i}")[:20]
        buttons.append(
            [
                InlineKeyboardButton(
                    f"🗑 Hapus #{i}: {t_name}",
                    callback_data=f"pl_do_del:{i}:{page}:{target_user_id}",
                    style=ButtonStyle.DANGER,
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "🔙 Kembali ke Playlist",
                callback_data=f"pl_page:{page}:{target_user_id}",
                style=ButtonStyle.PRIMARY,
            )
        ]
    )

    card = (
        "| 🗑 Pilih Lagu yang Ingin Dihapus |\n"
        "|:---:|\n"
        "| Klik tombol di bawah untuk menghapus lagu dari playlist Anda |\n\n"
        "| 🤖 Nusantara Stream 🤖 |\n"
        "|:---:|\n"
        "| |"
    )

    await RichParser.edit(query, card, reply_markup=InlineKeyboardMarkup(buttons))
    await query.answer()


@Client.on_callback_query(filters.regex(r"^pl_do_del:(\d+):(\d+):(\d+)"))
async def playlist_do_del_callback(client: Client, query: CallbackQuery):
    """Handler eksekusi hapus lagu dari callback tombol."""
    data = query.data.split(":")
    item_idx = int(data[1])
    page = int(data[2])
    target_user_id = int(data[3])

    if query.from_user and query.from_user.id != target_user_id:
        return await query.answer("⚠️ Anda hanya dapat mengubah playlist Anda sendiri.", show_alert=True)

    success, title = await db.remove_from_playlist(target_user_id, item_idx)
    if not success:
        return await query.answer(f"Gagal: {title}", show_alert=True)

    await query.answer(f"Lagu #{item_idx} berhasil dihapus!")

    tracks = await db.get_playlist(target_user_id)
    user_name = clean_markdown(query.from_user.first_name).replace("|", "\\|")
    card, total_pages = format_playlist_card(tracks, user_name, page=page)
    markup = get_playlist_keyboard(
        user_id=target_user_id,
        current_page=page,
        total_pages=total_pages,
        has_tracks=len(tracks) > 0,
    )

    await RichParser.edit(
        query,
        card,
        reply_markup=markup,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@Client.on_callback_query(filters.regex(r"^pl_clear_confirm:(\d+)"))
async def playlist_clear_confirm_callback(client: Client, query: CallbackQuery):
    """Konfirmasi sebelum mengosongkan seluruh playlist."""
    target_user_id = int(query.data.split(":")[1])
    if query.from_user and query.from_user.id != target_user_id:
        return await query.answer("⚠️ Anda hanya dapat mengubah playlist Anda sendiri.", show_alert=True)

    card = (
        "| ⚠️ Konfirmasi Pengosongan Playlist |\n"
        "|:---:|\n"
        "| Apakah Anda yakin ingin menghapus SELURUH lagu di playlist Anda? |\n\n"
        "| 🤖 Nusantara Stream 🤖 |\n"
        "|:---:|\n"
        "| |"
    )

    markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Ya, Kosongkan Semua",
                    callback_data=f"pl_do_clear:{target_user_id}",
                    style=ButtonStyle.DANGER,
                ),
                InlineKeyboardButton(
                    "❌ Batalkan",
                    callback_data=f"pl_page:1:{target_user_id}",
                    style=ButtonStyle.PRIMARY,
                ),
            ]
        ]
    )

    await RichParser.edit(query, card, reply_markup=markup)
    await query.answer()


@Client.on_callback_query(filters.regex(r"^pl_do_clear:(\d+)"))
async def playlist_do_clear_callback(client: Client, query: CallbackQuery):
    """Eksekusi pengosongan seluruh playlist."""
    target_user_id = int(query.data.split(":")[1])
    if query.from_user and query.from_user.id != target_user_id:
        return await query.answer("⚠️ Anda hanya dapat mengubah playlist Anda sendiri.", show_alert=True)

    deleted = await db.clear_playlist(target_user_id)
    await query.answer(f"Playlist berhasil dikosongkan ({deleted} lagu dihapus).")

    tracks = []
    user_name = clean_markdown(query.from_user.first_name).replace("|", "\\|")
    card, _ = format_playlist_card(tracks, user_name, page=1)
    markup = get_playlist_keyboard(
        user_id=target_user_id,
        current_page=1,
        total_pages=1,
        has_tracks=False,
    )

    await RichParser.edit(
        query,
        card,
        reply_markup=markup,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
