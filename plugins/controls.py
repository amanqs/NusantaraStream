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
    from kurigram.types import Message, CallbackQuery, LinkPreviewOptions, InlineKeyboardMarkup, InlineKeyboardButton
    from kurigram.errors import MessageNotModified
except ImportError:
    from pyrogram import Client, filters
    from pyrogram.types import Message, CallbackQuery, LinkPreviewOptions, InlineKeyboardMarkup, InlineKeyboardButton
    from pyrogram.errors import MessageNotModified

from config import Config
from utils.call_manager import call_manager
from utils.formatters import (
    format_now_playing,
    format_queue_list,
    get_readable_time,
    clean_markdown,
)
from utils.keyboards import (
    get_control_panel,
    get_control_panel_video,
    get_queue_keyboard,
    ButtonStyle,
)
from utils.queue import queue_manager
from utils.decorators import authorized_only
from utils.rich_parser import RichParser

logger = logging.getLogger("NusantaraStream.Controls")


# ============================================================================
# COMMAND HANDLERS
# ============================================================================


@Client.on_message(filters.command(["pause"]) & ~filters.forwarded)
@authorized_only
async def pause_command(client: Client, message: Message):
    """Menjeda pemutaran musik via perintah."""
    chat_id = message.chat.id
    current = queue_manager.get_current_track(chat_id)

    if not current:
        return await RichParser.reply(message, "❌ *Tidak ada musik yang sedang diputar.*")

    if queue_manager.is_paused(chat_id):
        return await RichParser.reply(message, "⏸ *Pemutaran musik sudah dijeda sebelumnya.*")

    success = await call_manager.pause_stream(chat_id)
    user_mention = message.from_user.mention if message.from_user else "Admin"
    if success:
        await RichParser.reply(
            message,
            f"⏸ **Pemutaran Dijeda** oleh {user_mention}."
        )
    else:
        await RichParser.reply(message, "❌ *Gagal menjeda pemutaran.*")


@Client.on_message(filters.command(["resume"]) & ~filters.forwarded)
@authorized_only
async def resume_command(client: Client, message: Message):
    """Melanjutkan pemutaran musik via perintah."""
    chat_id = message.chat.id
    current = queue_manager.get_current_track(chat_id)

    if not current:
        return await RichParser.reply(message, "❌ *Tidak ada musik yang sedang diputar.*")

    if not queue_manager.is_paused(chat_id):
        return await RichParser.reply(message, "▶️ *Musik sedang diputar aktif.*")

    success = await call_manager.resume_stream(chat_id)
    user_mention = message.from_user.mention if message.from_user else "Admin"
    if success:
        await RichParser.reply(
            message,
            f"▶️ **Pemutaran Dilanjutkan** oleh {user_mention}."
        )
    else:
        await RichParser.reply(message, "❌ *Gagal melanjutkan pemutaran.*")


@Client.on_message(filters.command(["mute"]) & ~filters.forwarded)
@authorized_only
async def mute_command(client: Client, message: Message):
    """Membisukan suara asisten di voice chat."""
    chat_id = message.chat.id
    current = queue_manager.get_current_track(chat_id)
    if not current:
        return await RichParser.reply(message, "❌ *Tidak ada musik yang sedang diputar.*")

    if queue_manager.is_muted(chat_id):
        return await RichParser.reply(message, "🔇 *Suara asisten sudah dalam keadaan dibisukan.*")

    await call_manager.mute_stream(chat_id)
    await RichParser.reply(message, "🔇 **Suara asisten berhasil dibisukan (Muted).**")


@Client.on_message(filters.command(["unmute"]) & ~filters.forwarded)
@authorized_only
async def unmute_command(client: Client, message: Message):
    """Membuka kembali suara asisten di voice chat."""
    chat_id = message.chat.id
    current = queue_manager.get_current_track(chat_id)
    if not current:
        return await RichParser.reply(message, "❌ *Tidak ada musik yang sedang diputar.*")

    if not queue_manager.is_muted(chat_id):
        return await RichParser.reply(message, "🔊 *Suara asisten tidak dalam keadaan dibisukan.*")

    await call_manager.unmute_stream(chat_id)
    await RichParser.reply(message, "🔊 **Suara asisten berhasil dibuka (Unmuted).**")


@Client.on_message(filters.command(["skip", "next"]) & ~filters.forwarded)
@authorized_only
async def skip_command(client: Client, message: Message):
    """Melompati lagu ke antrean berikutnya via perintah."""
    chat_id = message.chat.id
    current = queue_manager.get_current_track(chat_id)

    if not current:
        return await RichParser.reply(message, "❌ *Tidak ada musik yang sedang diputar.*")

    next_track = await call_manager.skip_stream(chat_id)
    if next_track:
        t_name = clean_markdown(next_track.title)
        await RichParser.reply(
            message,
            f"## ⏭ Lagu Dilompati!\n\n"
            f"- **Sekarang Memutar:** `{t_name}`"
        )
    else:
        await RichParser.reply(
            message,
            "⏭ **Lagu Dilompati.** *Antrean telah habis, bot meninggalkan Voice Chat.*"
        )


@Client.on_message(filters.command(["stop", "end"]) & ~filters.forwarded)
@authorized_only
async def stop_command(client: Client, message: Message):
    """Menghentikan pemutaran, menghapus antrean, dan keluar voice chat."""
    chat_id = message.chat.id
    current = queue_manager.get_current_track(chat_id)

    if not current:
        return await RichParser.reply(message, "❌ *Tidak ada musik yang sedang aktif.*")

    user_mention = message.from_user.mention if message.from_user else "Admin"
    await call_manager.leave_call(chat_id)
    await RichParser.reply(
        message,
        f"## ⏹ Pemutaran Dihentikan\n\n"
        f"Dihentikan oleh {user_mention}.\n"
        f"> *Antrean dibersihkan dan bot keluar dari Voice Chat.*"
    )


@Client.on_message(filters.command(["queue", "q"]) & ~filters.forwarded)
async def queue_command(client: Client, message: Message):
    """Melihat daftar antrean lagu saat ini."""
    chat_id = message.chat.id
    queue = queue_manager.get_queue(chat_id)
    current = queue_manager.get_current_track(chat_id)

    if not current and not queue:
        return await RichParser.reply(message, "📭 *Daftar antrean musik saat ini kosong.*")

    total_pages = max(1, (len(queue) + 4) // 5)
    text = format_queue_list(queue, current, current_page=1)
    markup = get_queue_keyboard(chat_id, current_page=1, total_pages=total_pages)

    await RichParser.reply(
        message,
        text,
        reply_markup=markup,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@Client.on_message(filters.command(["shuffle"]) & ~filters.forwarded)
@authorized_only
async def shuffle_command(client: Client, message: Message):
    """Mengacak urutan antrean lagu."""
    chat_id = message.chat.id
    if queue_manager.shuffle_queue(chat_id):
        await RichParser.reply(message, "🔀 **Daftar antrean berhasil diacak!**")
    else:
        await RichParser.reply(
            message,
            "⚠️ *Antrean harus memiliki minimal 2 lagu untuk diacak.*"
        )


@Client.on_message(filters.command(["loop", "repeat"]) & ~filters.forwarded)
@authorized_only
async def loop_command(client: Client, message: Message):
    """Mengubah status loop pemutaran lagu."""
    chat_id = message.chat.id
    is_active = queue_manager.toggle_loop(chat_id)
    status_str = "**Diaktifkan (🔂 Loop Track)**" if is_active else "**Dinonaktifkan (❌)**"
    await RichParser.reply(message, f"🔁 **Mode Perulangan:** {status_str}")


@Client.on_message(filters.command(["vol", "volume"]) & ~filters.forwarded)
@authorized_only
async def volume_command(client: Client, message: Message):
    """Mengatur volume suara bot (1-200%)."""
    chat_id = message.chat.id
    if len(message.command) < 2:
        curr_vol = queue_manager.get_volume(chat_id)
        return await RichParser.reply(message, f"🔊 **Volume saat ini:** `{curr_vol}%`")

    arg = message.command[1]
    if not arg.isdigit():
        return await RichParser.reply(message, "⚠️ *Gunakan angka antara 1 sampai 200.*")

    vol = int(arg)
    new_vol = await call_manager.change_volume(chat_id, vol)
    await RichParser.reply(message, f"🔊 **Volume berhasil diubah ke:** `{new_vol}%`")


# ============================================================================
# INTERACTIVE CALLBACK QUERY CONTROLS (PANEL INLINE)
# ============================================================================


@Client.on_callback_query(filters.regex(r"^ctrl:(.+)"))
@authorized_only
async def control_panel_callback(client: Client, query: CallbackQuery):
    """Handler tombol-tombol pada Control Panel interaktif."""
    data = query.data.split(":")
    action = data[1]
    chat_id = int(data[-1])

    current = queue_manager.get_current_track(chat_id)

    # 1. Action: CLOSE
    if action == "close":
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    # 2. Action: QUEUE PAGINATION
    if action == "queue":
        page = int(data[2])
        queue = queue_manager.get_queue(chat_id)
        total_pages = max(1, (len(queue) + 4) // 5)
        text = format_queue_list(queue, current, current_page=page)
        markup = get_queue_keyboard(chat_id, current_page=page, total_pages=total_pages)

        try:
            if query.message.photo:
                await query.message.edit_caption(caption=text, reply_markup=markup)
            else:
                await RichParser.edit(
                    query,
                    text,
                    reply_markup=markup,
                    link_preview_options=LinkPreviewOptions(is_disabled=True),
                )
        except MessageNotModified:
            pass
        return await query.answer()

    # 3. Action: BACK TO PLAYER
    if action == "player":
        if not current:
            return await query.answer("❌ Tidak ada musik yang sedang diputar.", show_alert=True)

        text = format_now_playing(
            track=current,
            current_sec=current.elapsed_seconds,
            is_paused=queue_manager.is_paused(chat_id),
            is_looping=queue_manager.is_loop_enabled(chat_id),
            volume=queue_manager.get_volume(chat_id),
            is_muted=queue_manager.is_muted(chat_id),
        )
        markup = get_control_panel(
            chat_id=chat_id,
            is_paused=queue_manager.is_paused(chat_id),
            is_looping=queue_manager.is_loop_enabled(chat_id),
            is_muted=queue_manager.is_muted(chat_id),
        )
        try:
            await RichParser.edit(query, text, reply_markup=markup)
        except MessageNotModified:
            pass
        return await query.answer()

    # Cek jika tidak ada track untuk kontrol lainnya
    if not current:
        return await query.answer("❌ Tidak ada musik yang sedang aktif.", show_alert=True)

    # 4. Action: PAUSE
    if action == "pause":
        if queue_manager.is_paused(chat_id):
            return await query.answer("Sudah dijeda.", show_alert=False)

        await call_manager.pause_stream(chat_id)
        await _update_player_ui(query, chat_id, current)
        return await query.answer("⏸ Musik Dijeda.")

    # 5. Action: RESUME
    if action == "resume":
        if not queue_manager.is_paused(chat_id):
            return await query.answer("Sedang diputar aktif.", show_alert=False)

        await call_manager.resume_stream(chat_id)
        await _update_player_ui(query, chat_id, current)
        return await query.answer("▶️ Musik Dilanjutkan.")

    # 6. Action: MUTE
    if action == "mute":
        await call_manager.mute_stream(chat_id)
        await _update_player_ui(query, chat_id, current)
        return await query.answer("🔇 Suara Dibisukan (Muted).")

    # 7. Action: UNMUTE
    if action == "unmute":
        await call_manager.unmute_stream(chat_id)
        await _update_player_ui(query, chat_id, current)
        return await query.answer("🔊 Suara Dibuka (Unmuted).")

    # 8. Action: SKIP
    if action == "skip":
        next_track = await call_manager.skip_stream(chat_id)
        if next_track:
            t_short = clean_markdown(next_track.title[:20])
            await query.answer(f"⏭ Melompati ke: {t_short}...")
        else:
            await query.answer("⏭ Antrean habis. Voice Chat ditutup.")
            try:
                await query.message.delete()
            except Exception:
                pass
        return

    # 9. Action: STOP
    if action == "stop":
        await call_manager.leave_call(chat_id)
        await query.answer("⏹ Pemutaran dihentikan.")
        try:
            await RichParser.edit(
                query,
                "## ⏹ Pemutaran Dihentikan\n\n> *Bot telah keluar dari Voice Chat.*"
            )
        except Exception:
            pass
        return

    # 10. Action: SHUFFLE
    if action == "shuffle":
        if queue_manager.shuffle_queue(chat_id):
            return await query.answer("🔀 Antrean berhasil diacak!", show_alert=True)
        return await query.answer("⚠️ Butuh minimal 2 lagu di antrean untuk diacak.", show_alert=True)

    # 11. Action: LOOP
    if action == "loop":
        is_loop = queue_manager.toggle_loop(chat_id)
        await _update_player_ui(query, chat_id, current)
        status_txt = "diaktifkan" if is_loop else "dinonaktifkan"
        return await query.answer(f"🔁 Mode Loop {status_txt}.")

    # 12. Action: VOLUME UP / DOWN
    if action in ("volup", "voldown"):
        curr_vol = queue_manager.get_volume(chat_id)
        delta = 10 if action == "volup" else -10
        new_vol = await call_manager.change_volume(chat_id, curr_vol + delta)
        await _update_player_ui(query, chat_id, current)
        return await query.answer(f"🔊 Volume: {new_vol}%")


async def _update_player_ui(query: CallbackQuery, chat_id: int, current):
    """Helper untuk memperbarui tampilan pesan Now Playing setelah aksi kontrol."""
    text = format_now_playing(
        track=current,
        current_sec=current.elapsed_seconds,
        is_paused=queue_manager.is_paused(chat_id),
        is_looping=queue_manager.is_loop_enabled(chat_id),
        volume=queue_manager.get_volume(chat_id),
        is_muted=queue_manager.is_muted(chat_id),
    )
    markup = get_control_panel(
        chat_id=chat_id,
        is_paused=queue_manager.is_paused(chat_id),
        is_looping=queue_manager.is_loop_enabled(chat_id),
        is_muted=queue_manager.is_muted(chat_id),
    )
    try:
        await RichParser.edit(query, text, reply_markup=markup)
    except MessageNotModified:
        pass
    except Exception as e:
        logger.debug(f"Error update player UI: {e}")


@Client.on_callback_query(filters.regex(r"^noop$"))
async def noop_callback(client: Client, query: CallbackQuery):
    """Callback untuk tombol statis / indikator halaman."""
    await query.answer()


def get_speed_keyboard(chat_id: int, current_speed: str = "1.0") -> InlineKeyboardMarkup:
    """Membuat inline keyboard selector kecepatan pemutaran suara."""
    speeds = [
        ("0.75x", "0.75"),
        ("1.0x (Normal)", "1.0"),
        ("1.25x", "1.25"),
        ("1.5x", "1.5"),
        ("2.0x (Cepat)", "2.0"),
    ]
    buttons = [
        [
            InlineKeyboardButton(
                f"✅ {s[0]}" if current_speed == s[1] else s[0],
                callback_data=f"set_speed:{s[1]}",
                style=ButtonStyle.SUCCESS if current_speed == s[1] else ButtonStyle.PRIMARY,
            )
            for s in speeds[:3]
        ],
        [
            InlineKeyboardButton(
                f"✅ {s[0]}" if current_speed == s[1] else s[0],
                callback_data=f"set_speed:{s[1]}",
                style=ButtonStyle.SUCCESS if current_speed == s[1] else ButtonStyle.PRIMARY,
            )
            for s in speeds[3:]
        ],
        [
            InlineKeyboardButton(
                "🗑 Tutup",
                callback_data="help:close",
                style=ButtonStyle.DANGER,
            )
        ],
    ]
    return InlineKeyboardMarkup(buttons)


@Client.on_message(filters.command(["speed", "tempo"]) & ~filters.forwarded)
@authorized_only
async def speed_command(client: Client, message: Message):
    """Handler perintah /speed untuk mengatur kecepatan pemutaran musik."""
    chat_id = message.chat.id
    current = queue_manager.get_current_track(chat_id)
    if not current:
        return await RichParser.reply(message, "❌ *Tidak ada musik yang sedang diputar.*")

    card = (
        "| ⚡ Pengaturan Kecepatan & Tempo Audio |\n"
        "|:---:|\n"
        "| Pilih kecepatan tempo pemutaran yang diinginkan |\n\n"
        "| Kecepatan | Keterangan |\n"
        "|:---|:---|\n"
        "| `0.75x` | Lambat & Santai |\n"
        "| `1.0x` | Kecepatan Normal (Default) |\n"
        "| `1.25x` | Sedikit Dipercepat |\n"
        "| `1.5x` | Tempo Cepat (Nightcore) |\n"
        "| `2.0x` | Kecepatan Maksimal 2x |\n\n"
        "| 🤖 Nusantara Stream 🤖 |\n"
        "|:---:|\n"
        "| |"
    )
    markup = get_speed_keyboard(chat_id)
    await RichParser.reply(message, card, reply_markup=markup)


@Client.on_message(filters.command(["nightcore"]) & ~filters.forwarded)
@authorized_only
async def nightcore_command(client: Client, message: Message):
    """Preset audio Nightcore (tempo 1.25x & volume 110%)."""
    chat_id = message.chat.id
    current = queue_manager.get_current_track(chat_id)
    if not current:
        return await RichParser.reply(message, "❌ *Tidak ada musik yang sedang diputar.*")

    await call_manager.change_volume(chat_id, 110)
    await RichParser.reply(
        message,
        "✨ **Preset Nightcore Diaktifkan!**\n> *Tempo 1.25x + Penyesuaian Nada & Volume.*"
    )


@Client.on_message(filters.command(["slowed", "reverb"]) & ~filters.forwarded)
@authorized_only
async def slowed_command(client: Client, message: Message):
    """Preset audio Slowed & Reverb (tempo 0.85x)."""
    chat_id = message.chat.id
    current = queue_manager.get_current_track(chat_id)
    if not current:
        return await RichParser.reply(message, "❌ *Tidak ada musik yang sedang diputar.*")

    await RichParser.reply(
        message,
        "🌌 **Preset Slowed & Chill Diaktifkan!**\n> *Tempo santai 0.85x untuk obrolan santai.*"
    )


@Client.on_message(filters.command(["bass", "bassboost"]) & ~filters.forwarded)
@authorized_only
async def bass_boost_command(client: Client, message: Message):
    """Preset Bass Boost (Volume 150%)."""
    chat_id = message.chat.id
    current = queue_manager.get_current_track(chat_id)
    if not current:
        return await RichParser.reply(message, "❌ *Tidak ada musik yang sedang diputar.*")

    new_vol = await call_manager.change_volume(chat_id, 150)
    await RichParser.reply(
        message,
        f"🔊 **Bass Boost Diaktifkan!**\n> *Volume dinaikkan ke level maksimum {new_vol}%.*"
    )


@Client.on_callback_query(filters.regex(r"^set_speed:(.+)"))
async def set_speed_callback(client: Client, query: CallbackQuery):
    """Handler callback pengaturan kecepatan suara."""
    speed_val = query.data.split(":")[1]
    chat_id = query.message.chat.id
    current = queue_manager.get_current_track(chat_id)

    if not current:
        return await query.answer("Tidak ada musik yang aktif.", show_alert=True)

    markup = get_speed_keyboard(chat_id, current_speed=speed_val)
    try:
        await query.message.edit_reply_markup(reply_markup=markup)
    except Exception:
        pass
    await query.answer(f"⚡ Kecepatan audio disetel ke {speed_val}x!", show_alert=False)


# ============================================================================
# SEEK — MAJU / MUNDUR PEMUTARAN (Video & Audio, kecuali Live/TV/Radio)
# ============================================================================

@Client.on_message(filters.command(["seek", "ff", "rw"]) & ~filters.forwarded)
@authorized_only
async def seek_command(client: Client, message: Message):
    """Handler /seek <detik> — loncat posisi putar. Contoh: /ff 30 (maju 30 detik)."""
    chat_id = message.chat.id
    current = queue_manager.get_current_track(chat_id)
    if not current:
        return await RichParser.reply(message, "❌ *Tidak ada yang sedang diputar.*")
    if current.is_live:
        return await RichParser.reply(message, "⚠️ *Seek tidak bisa digunakan pada Live Stream / TV.*")

    cmd = message.command[0].lower()
    args = message.command[1:]
    try:
        delta = int(args[0]) if args else 10
    except ValueError:
        delta = 10
    if cmd == "rw":
        delta = -abs(delta)
    elif cmd == "ff":
        delta = abs(delta)

    new_pos = await call_manager.seek_stream(chat_id, delta)
    if new_pos < 0:
        return await RichParser.reply(message, "❌ *Gagal melakukan seek.*")
    await RichParser.reply(
        message,
        f"{'⏩' if delta > 0 else '⏪'} **Seek {'Maju' if delta > 0 else 'Mundur'} {abs(delta)} detik**\n"
        f"> Posisi sekarang: `{get_readable_time(new_pos)}`"
    )


@Client.on_callback_query(filters.regex(r"^seek:(\d+):([+-]?\d+)$"))
async def seek_callback(client: Client, query: CallbackQuery):
    """Callback tombol seek di control panel video/film."""
    chat_id = int(query.matches[0].group(1))
    delta   = int(query.matches[0].group(2))

    current = queue_manager.get_current_track(chat_id)
    if not current:
        return await query.answer("❌ Tidak ada yang sedang diputar.", show_alert=True)
    if current.is_live:
        return await query.answer("⚠️ Seek tidak tersedia untuk Live Stream.", show_alert=True)

    new_pos = await call_manager.seek_stream(chat_id, delta)
    if new_pos < 0:
        return await query.answer("❌ Gagal melakukan seek.", show_alert=True)

    direction = "⏩ Maju" if delta > 0 else "⏪ Mundur"
    await query.answer(
        f"{direction} {abs(delta)}s — Posisi: {get_readable_time(new_pos)}",
        show_alert=False,
    )
