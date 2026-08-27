# ==============================================================================
#  🇮🇩 Nusantara Stream - Telegram Music & Video Streaming Bot
# ==============================================================================
#  Author   : Amang (@BukanDevelopers)
#  GitHub   : https://github.com/amanqs
#  Project  : Nusantara Stream Telegram Bot
#  License  : GNU General Public License v3.0
# ==============================================================================

import time
import os

try:
    from kurigram import Client, filters
    from kurigram.types import Message, CallbackQuery, LinkPreviewOptions
except ImportError:
    from pyrogram import Client, filters
    from pyrogram.types import Message, CallbackQuery, LinkPreviewOptions

from config import Config
from utils.keyboards import get_start_keyboard, get_help_keyboard
from utils.formatters import clean_markdown
from utils.rich_parser import RichParser
from utils.database import db

START_TIME = time.time()

@Client.on_message(filters.command(["start"]) & ~filters.forwarded)
async def start_handler(client: Client, message: Message):
    """Handler perintah /start bergaya Native Blockquote Telegram."""
    chat = message.chat
    user = message.from_user
    user_name = clean_markdown(user.first_name if user and user.first_name else "Pengguna")

    # Rekam user / grup ke database
    if user:
        await db.add_served_user(user.id, user.first_name, user.username)
    if chat.type.value in ("group", "supergroup", "channel"):
        await db.add_served_chat(chat.id, chat.title, str(chat.type))

    # Ambil username bot secara aman
    bot_user = client.me.username if getattr(client, "me", None) else Config.BOT_USERNAME

    # Cek Deep-Linking parameter dari tombol Inline Query / Share Link
    if len(message.command) > 1:
        param = message.command[1]

        if param.startswith("play_"):
            vid_id = param[5:]
            if chat.type.value in ("group", "supergroup"):
                message.text = f"/play https://www.youtube.com/watch?v={vid_id}"
                message.command = ["play", f"https://www.youtube.com/watch?v={vid_id}"]
                from plugins.play import play_command
                return await play_command(client, message)
            else:
                return await RichParser.reply(
                    message,
                    "ℹ️ **Perintah Pemutaran Musik:**\n"
                    "> Tambahkan saya ke grup Anda dan jadikan admin untuk memutar lagu di Voice Chat!\n\n"
                    f"*Lagu yang dipilih:* `https://www.youtube.com/watch?v={vid_id}`",
                    reply_markup=get_start_keyboard(bot_user),
                )

        elif param.startswith("vplay_"):
            vid_id = param[6:]
            if chat.type.value in ("group", "supergroup"):
                message.text = f"/vplay https://www.youtube.com/watch?v={vid_id}"
                message.command = ["vplay", f"https://www.youtube.com/watch?v={vid_id}"]
                from plugins.play import vplay_command
                return await vplay_command(client, message)
            else:
                return await RichParser.reply(
                    message,
                    "ℹ️ **Perintah Pemutaran Video:**\n"
                    "> Tambahkan saya ke grup Anda dan jadikan admin untuk memutar video di Voice Chat!\n\n"
                    f"*Video yang dipilih:* `https://www.youtube.com/watch?v={vid_id}`",
                    reply_markup=get_start_keyboard(bot_user),
                )

        elif param.startswith("song_"):
            vid_id = param[5:]
            message.text = f"/song https://www.youtube.com/watch?v={vid_id}"
            message.command = ["song", f"https://www.youtube.com/watch?v={vid_id}"]
            from plugins.downloader import song_downloader_command
            return await song_downloader_command(client, message)

        elif param.startswith("video_"):
            vid_id = param[6:]
            message.text = f"/video https://www.youtube.com/watch?v={vid_id}"
            message.command = ["video", f"https://www.youtube.com/watch?v={vid_id}"]
            from plugins.downloader import video_downloader_command
            return await video_downloader_command(client, message)

        elif param == "help_radio":
            from plugins.radio import radio_menu_command
            return await radio_menu_command(client, message)

        elif param in ("help_tv", "tv", "iptv"):
            from plugins.tv import tv_menu_command
            return await tv_menu_command(client, message)

    # Tampilan Table Card
    user_name = clean_markdown(user.first_name if user and user.first_name else "Pengguna").replace("|", "\\|")

    welcome_text = (
        f"| 👋 Halo, {user_name}! |\n"
        f"|:---:|\n"
        f"| Selamat datang di {Config.BOT_NAME} |\n\n"
        f"| Fitur Unggulan | Keterangan Sistem |\n"
        f"|:---|:---|\n"
        f"| 🎵 Audio HQ | Streaming jernih tanpa jeda |\n"
        f"| 🎬 Video HD | Kualitas visual jernih hingga 720p |\n"
        f"| 📥 Downloader | Unduh MP3 & MP4 langsung ke chat |\n"
        f"| 📂 Playlist | Simpan & putar lagu favorit Anda |\n"
        f"| 🔍 Inline Search | Cari lagu langsung via `@{bot_user}` |\n"
        f"| 📜 Lirik Lagu | Pencarian lirik otomatis jutaan lagu |\n"
        f"| 📻 Radio 24/7 | Putar stasiun Radio Indonesia di VC |\n"
        f"| 🎛 Control Panel | Tombol kontrol interaktif lengkap |\n"
        f"| ⚡ Speed & Effects | Nightcore, Slowed & Bass Boost |\n"
        f"| ⚙️ Group Settings | Konfigurasi preferensi grup mandiri |\n"
        f"| 👨‍💻 Pengembang | Amang (@BukanDevelopers) |\n\n"
        f"| 💡 Tambahkan saya ke grup Anda untuk mulai memutar lagu! |\n"
        f"|:---:|\n"
        f"| |"
    )

    markup = get_start_keyboard(bot_user)
    await RichParser.reply(
        message,
        welcome_text,
        reply_markup=markup,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@Client.on_message(filters.command(["help"]) & ~filters.forwarded)
async def help_handler(client: Client, message: Message):
    """Handler perintah /help bergaya Telegram Pure Markdown Table Card."""
    if message.from_user:
        await db.add_served_user(message.from_user.id, message.from_user.first_name, message.from_user.username)
    if message.chat.type.value in ("group", "supergroup", "channel"):
        await db.add_served_chat(message.chat.id, message.chat.title, str(message.chat.type))

    db_stats = await db.get_db_stats()
    users_cnt = db_stats.get("users", 0)
    chats_cnt = db_stats.get("chats", 0)

    help_text = (
        f"| 🤖 Panduan Penggunaan — {Config.BOT_NAME} |\n"
        f"|:---:|\n"
        f"| Pilih kategori menu di bawah untuk melihat perintah lengkap |\n\n"
        f"| Statistik Sistem | Detail Jumlah |\n"
        f"|:---|:---|\n"
        f"| 📢 Served Chats | `{chats_cnt:,} grup` |\n"
        f"| 👥 Served Users | `{users_cnt:,} pengguna` |\n"
        f"| 🤖 Engine | `Kurigram + PyTgCalls v2.3.3` |\n\n"
        f"| 💡 Klik tombol kategori di bawah untuk membuka panduan: |\n"
        f"|:---:|\n"
        f"| |"
    )

    markup = get_help_keyboard("main")
    await RichParser.reply(
        message,
        help_text,
        reply_markup=markup,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@Client.on_message(filters.command(["ping", "stats"]) & ~filters.forwarded)
async def ping_handler(client: Client, message: Message):
    """Handler perintah /ping & /stats untuk cek latensi & statistik bot bergaya Table Card."""
    start = time.time()
    reply = await RichParser.reply(message, "⚡ *Memeriksa status & latensi server...*")
    delta_ms = (time.time() - start) * 1000
    uptime_sec = int(time.time() - START_TIME)

    hours = uptime_sec // 3600
    mins = (uptime_sec % 3600) // 60
    secs = uptime_sec % 60
    uptime_str = f"{hours}j {mins}m {secs}d"

    db_stats = await db.get_db_stats()
    users_cnt = db_stats.get("users", 0)
    chats_cnt = db_stats.get("chats", 0)

    text = (
        f"| 🏓 Status & Statistik {Config.BOT_NAME} |\n"
        f"|:---:|\n"
        f"| |\n\n"
        f"| Metrik Sistem | Nilai Status |\n"
        f"|:---|:---|\n"
        f"| ⚡ Respon Bot | `{delta_ms:.2f} ms` |\n"
        f"| ⏳ Uptime | `{uptime_str}` |\n"
        f"| 👥 Pengguna Terdaftar | `{users_cnt:,} pengguna` |\n"
        f"| 📢 Grup Terlayani | `{chats_cnt:,} grup` |\n"
        f"| 🤖 Engine | Kurigram + PyTgCalls v2.3.3 |\n\n"
        f"| 🤖 Nusantara Stream 🤖 |\n"
        f"|:---:|\n"
        f"| |"
    )
    await RichParser.edit(reply, text)


@Client.on_callback_query(filters.regex(r"^help:(.+)"))
async def help_callback_handler(client: Client, query: CallbackQuery):
    """Handler navigasi tab bantuan via callback inline dengan Rich Markdown Table Card."""
    action = query.data.split(":", 1)[1]

    if action == "close":
        try:
            await query.message.delete()
        except Exception:
            pass
        return await query.answer("Menu ditutup.")

    user_name = clean_markdown(query.from_user.first_name if query.from_user else "Pengguna").replace("|", "\\|")

    if action == "back_start":
        bot_user = client.me.username if getattr(client, "me", None) else Config.BOT_USERNAME
        welcome_text = (
            f"| 👋 Halo, {user_name}! |\n"
            f"|:---:|\n"
            f"| Selamat datang di {Config.BOT_NAME} |\n\n"
            f"| Fitur Unggulan | Keterangan Sistem |\n"
            f"|:---|:---|\n"
            f"| 🎵 Audio HQ | Streaming jernih tanpa jeda |\n"
            f"| 🎬 Video HD | Kualitas visual jernih hingga 720p |\n"
            f"| 📥 Downloader | Unduh MP3 & MP4 langsung ke chat |\n"
            f"| 📂 Playlist | Simpan & putar lagu favorit Anda |\n"
            f"| 🔍 Inline Search | Cari lagu via `@{bot_user}` |\n"
            f"| 📜 Lirik Lagu | Pencarian lirik otomatis jutaan lagu |\n"
            f"| 📻 Radio 24/7 | Putar stasiun Radio Indonesia di VC |\n"
            f"| 🎛 Control Panel | Tombol kontrol interaktif lengkap |\n"
            f"| ⚡ Speed & Effects | Nightcore, Slowed & Bass Boost |\n"
            f"| ⚙️ Group Settings | Konfigurasi preferensi grup mandiri |\n\n"
            f"| 💡 Tambahkan saya ke grup Anda untuk mulai memutar lagu! |\n"
            f"|:---:|\n"
            f"| |"
        )
        markup = get_start_keyboard(bot_user)
        try:
            await RichParser.edit(
                query,
                welcome_text,
                reply_markup=markup,
                link_preview_options=LinkPreviewOptions(is_disabled=True),
            )
        except Exception:
            pass
        await query.answer()
        return

    if action.startswith("page:"):
        try:
            page = int(action.split(":")[1])
        except ValueError:
            page = 1
        action = f"page_{page}"

    db_stats = await db.get_db_stats()
    users_cnt = db_stats.get("users", 0)
    chats_cnt = db_stats.get("chats", 0)

    help_texts = {
        "play": (
            f"| 🎵 Panduan Audio Play — {Config.BOT_NAME} |\n"
            f"|:---:|\n"
            f"| Perintah memutar musik di Voice Chat |\n\n"
            f"| Perintah | Keterangan Fungsi |\n"
            f"|:---|:---|\n"
            f"| `/play (judul/link)` | Putar audio YouTube di VC |\n"
            f"| `/play` (balas audio) | Putar berkas audio Telegram |\n"
            f"| `/playforce (judul)` | Putar lagu lewati antrean |\n"
            f"| `/seek (detik)` / `/ff` | Lompat maju / mundur audio |\n"
            f"| `/rw (detik)` | Mundur posisi pemutaran |\n\n"
            f"| 🤖 Nusantara Stream 🤖 |\n"
            f"|:---:|\n"
            f"| |"
        ),
        "playlist": (
            f"| 📂 Panduan Playlist — {Config.BOT_NAME} |\n"
            f"|:---:|\n"
            f"| Manajemen daftar putar lagu pribadi |\n\n"
            f"| Perintah | Keterangan Fungsi |\n"
            f"|:---|:---|\n"
            f"| `/playlist` / `/myplaylist` | Buka daftar playlist pribadi |\n"
            f"| `/save (judul/link)` | Simpan lagu ke playlist |\n"
            f"| `/playplaylist` | Putar semua lagu di playlist |\n"
            f"| `/delplaylist (no)` | Hapus lagu dari playlist |\n\n"
            f"| 🤖 Nusantara Stream 🤖 |\n"
            f"|:---:|\n"
            f"| |"
        ),
        "queue": (
            f"| 📦 Panduan Queue & Antrean — {Config.BOT_NAME} |\n"
            f"|:---:|\n"
            f"| Pengaturan antrean pemutaran lagu |\n\n"
            f"| Perintah | Keterangan Fungsi |\n"
            f"|:---|:---|\n"
            f"| `/queue` / `/q` | Tampilkan antrean lagu saat ini |\n"
            f"| `/shuffle` | Acak urutan daftar antrean |\n"
            f"| `/loop (1-10/off)` | Putar berulang lagu x kali |\n"
            f"| `/np` / `/nowplaying` | Tampilkan kartu lagu aktif |\n\n"
            f"| 🤖 Nusantara Stream 🤖 |\n"
            f"|:---:|\n"
            f"| |"
        ),
        "control": (
            f"| 🎛️ Panduan Kontrol Player — {Config.BOT_NAME} |\n"
            f"|:---:|\n"
            f"| Tombol navigasi dan volume pemutar |\n\n"
            f"| Perintah | Keterangan Fungsi |\n"
            f"|:---|:---|\n"
            f"| `/pause` / `/resume` | Jeda atau lanjutkan media |\n"
            f"| `/skip` / `/next` | Lewati lagu ke berikutnya |\n"
            f"| `/stop` / `/end` | Hentikan pemutaran & reset |\n"
            f"| `/volume (1-200)` | Atur volume pemutaran musik |\n"
            f"| `/mute` / `/unmute` | Bisukan / aktifkan suara |\n\n"
            f"| 🤖 Nusantara Stream 🤖 |\n"
            f"|:---:|\n"
            f"| |"
        ),
        "film": (
            f"| 🎬 Panduan Film Bioskop — {Config.BOT_NAME} |\n"
            f"|:---:|\n"
            f"| Streaming film dari channel privat di VC |\n\n"
            f"| Perintah | Keterangan Fungsi |\n"
            f"|:---|:---|\n"
            f"| `/film` / `/movie` | Buka katalog bioskop di VC |\n"
            f"| `/film (judul)` | Cari & putar film privat |\n"
            f"| `/seek (detik)` / `/ff` | Lompat maju / mundur film |\n\n"
            f"| 🤖 Nusantara Stream 🤖 |\n"
            f"|:---:|\n"
            f"| |"
        ),
        "video": (
            f"| 🎥 Panduan Video HD — {Config.BOT_NAME} |\n"
            f"|:---:|\n"
            f"| Streaming video 720p HD di Voice Chat |\n\n"
            f"| Perintah | Keterangan Fungsi |\n"
            f"|:---|:---|\n"
            f"| `/vplay (judul/link)` | Putar video YouTube 720p |\n"
            f"| `/vplay` (balas video) | Putar berkas file video |\n"
            f"| `/vplayforce (judul)` | Putar video lewati antrean |\n"
            f"| `/seek (detik)` / `/ff` | Lompat maju / mundur video |\n\n"
            f"| 🤖 Nusantara Stream 🤖 |\n"
            f"|:---:|\n"
            f"| |"
        ),
        "tv": (
            f"| 📺 Panduan Live TV — {Config.BOT_NAME} |\n"
            f"|:---:|\n"
            f"| Siaran TV Nasional Indonesia di VC |\n\n"
            f"| Perintah | Keterangan Fungsi |\n"
            f"|:---|:---|\n"
            f"| `/tv` / `/iptv` | Menu Live TV & ganti channel |\n"
            f"| `/tv (link m3u8)` | Putar siaran IPTV kustom |\n\n"
            f"| 🤖 Nusantara Stream 🤖 |\n"
            f"|:---:|\n"
            f"| |"
        ),
        "radio": (
            f"| 📻 Panduan Radio 24/7 — {Config.BOT_NAME} |\n"
            f"|:---:|\n"
            f"| Streaming Radio Nasional nonstop di VC |\n\n"
            f"| Perintah | Keterangan Fungsi |\n"
            f"|:---|:---|\n"
            f"| `/radio` | Putar siaran Radio 24/7 |\n"
            f"| `/autoplay (on/off)` | Putar rekomendasi otomatis |\n\n"
            f"| 🤖 Nusantara Stream 🤖 |\n"
            f"|:---:|\n"
            f"| |"
        ),
        "effects": (
            f"| ⚡ Panduan Efek Audio — {Config.BOT_NAME} |\n"
            f"|:---:|\n"
            f"| Modifikasi tempo & efek suara realtime |\n\n"
            f"| Perintah | Keterangan Fungsi |\n"
            f"|:---|:---|\n"
            f"| `/speed (0.5-2.0)` | Ubah tempo lagu presisi |\n"
            f"| `/nightcore` | Efek nada tinggi & cepat (1.25x) |\n"
            f"| `/slowed` | Efek santai tempo lambat (0.85x) |\n"
            f"| `/bass` / `/bassboost` | Efek penguat bass frekuensi |\n"
            f"| `/speed 1.0` | Kembalikan tempo ke normal |\n\n"
            f"| 🤖 Nusantara Stream 🤖 |\n"
            f"|:---:|\n"
            f"| |"
        ),
        "download": (
            f"| 📥 Panduan Unduh File — {Config.BOT_NAME} |\n"
            f"|:---:|\n"
            f"| Unduh file MP3 & Video HD ke chat |\n\n"
            f"| Perintah | Keterangan Fungsi |\n"
            f"|:---|:---|\n"
            f"| `/song (judul/link)` | Unduh file MP3 320kbps + Art |\n"
            f"| `/video (judul/link)` | Unduh video HD 720p MP4 |\n\n"
            f"| 🤖 Nusantara Stream 🤖 |\n"
            f"|:---:|\n"
            f"| |"
        ),
        "lyrics": (
            f"| 📜 Panduan Lirik Lagu — {Config.BOT_NAME} |\n"
            f"|:---:|\n"
            f"| Pencarian lirik lagu jutaan judul |\n\n"
            f"| Perintah | Keterangan Fungsi |\n"
            f"|:---|:---|\n"
            f"| `/lyrics (judul)` | Cari & tampilkan lirik lagu |\n\n"
            f"| 🤖 Nusantara Stream 🤖 |\n"
            f"|:---:|\n"
            f"| |"
        ),
        "search": (
            f"| 🔍 Panduan Pencarian Inline — {Config.BOT_NAME} |\n"
            f"|:---:|\n"
            f"| Cari lagu via inline query di chat mana pun |\n\n"
            f"| Format | Keterangan Fungsi |\n"
            f"|:---|:---|\n"
            f"| `@{Config.BOT_USERNAME} (judul)` | Cari lagu langsung di chat |\n\n"
            f"| 🤖 Nusantara Stream 🤖 |\n"
            f"|:---:|\n"
            f"| |"
        ),
        "admin": (
            f"| 🛡️ Panduan Admin Grup — {Config.BOT_NAME} |\n"
            f"|:---:|\n"
            f"| Pengaturan hak akses di Voice Chat |\n\n"
            f"| Perintah | Keterangan Fungsi |\n"
            f"|:---|:---|\n"
            f"| `/settings` | Panel preferensi grup interaktif |\n"
            f"| `/auth (reply/id)` | Beri izin non-admin kontrol |\n"
            f"| `/unauth (reply/id)` | Cabut izin kontrol member |\n"
            f"| `/authlist` | Daftar user terotorisasi |\n\n"
            f"| 🤖 Nusantara Stream 🤖 |\n"
            f"|:---:|\n"
            f"| |"
        ),
        "settings": (
            f"| ⚙️ Panduan Settings Grup — {Config.BOT_NAME} |\n"
            f"|:---:|\n"
            f"| Konfigurasi preferensi pemutar di grup |\n\n"
            f"| Perintah | Keterangan Fungsi |\n"
            f"|:---|:---|\n"
            f"| `/settings` | Buka panel pengaturan grup |\n"
            f"| ℹ️ Fitur | Mode Admin, CleanMode, PlayType |\n\n"
            f"| 🤖 Nusantara Stream 🤖 |\n"
            f"|:---:|\n"
            f"| |"
        ),
        "auth": (
            f"| 🔐 Panduan Otorisasi — {Config.BOT_NAME} |\n"
            f"|:---:|\n"
            f"| Kelola user yang berhak mengontrol pemutar |\n\n"
            f"| Perintah | Keterangan Fungsi |\n"
            f"|:---|:---|\n"
            f"| `/auth (reply/id)` | Tambah user ke daftar auth |\n"
            f"| `/unauth (reply/id)` | Hapus user dari daftar auth |\n"
            f"| `/authlist` | Tampilkan user terotorisasi |\n"
            f"| ℹ️ Catatan | Peminta lagu otomatis bisa kontrol |\n\n"
            f"| 🤖 Nusantara Stream 🤖 |\n"
            f"|:---:|\n"
            f"| |"
        ),
        "sudo": (
            f"| 👑 Panduan Sudo Admin — {Config.BOT_NAME} |\n"
            f"|:---:|\n"
            f"| Manajemen server & operasional bot |\n\n"
            f"| Perintah | Keterangan Fungsi |\n"
            f"|:---|:---|\n"
            f"| `/broadcast` | Broadcast ke semua user & grup |\n"
            f"| `/activevc` | Cek Voice Chat aktif berjalan |\n"
            f"| `/clean` | Bersihkan berkas cache server |\n"
            f"| `/sysinfo` | Statistik CPU, RAM & Server |\n"
            f"| `/sudolist` | Daftar Sudo Admin & Owner |\n"
            f"| `/reload` | (Hot Reload) Muat ulang kode |\n"
            f"| `/restart` | Restart bot aman & reconnect |\n"
            f"| `/logs` | Unduh berkas log diagnosa |\n\n"
            f"| 🤖 Nusantara Stream 🤖 |\n"
            f"|:---:|\n"
            f"| |"
        ),
        "owner": (
            f"| 🗄️ Panduan Owner & Database — {Config.BOT_NAME} |\n"
            f"|:---:|\n"
            f"| Akses database SQLite & eksekusi kode |\n\n"
            f"| Perintah | Keterangan Fungsi |\n"
            f"|:---|:---|\n"
            f"| `/backup` | Unduh database SQLite .db |\n"
            f"| `/autobackup` | Konfigurasi backup harian |\n"
            f"| `/restore` | Pulihkan file database .db |\n"
            f"| `/addsudo (id/user)` | Tambah Sudo Admin baru |\n"
            f"| `/delsudo (id/user)` | Hapus Sudo Admin dari sistem |\n"
            f"| `/eval (kode)` | Eksekusi potongan kode Python |\n"
            f"| `/sh (perintah)` | Jalankan perintah shell Linux |\n\n"
            f"| 🤖 Nusantara Stream 🤖 |\n"
            f"|:---:|\n"
            f"| |"
        ),
        "info": (
            f"| ℹ️ Informasi Sistem & Statistik — {Config.BOT_NAME} |\n"
            f"|:---:|\n"
            f"| Detail status operasional dan engine bot |\n\n"
            f"| Perintah | Keterangan Fungsi |\n"
            f"|:---|:---|\n"
            f"| `/start` | Tampilkan pesan sambutan awal |\n"
            f"| `/help` | Buka menu pusat bantuan |\n"
            f"| `/ping` | Cek latensi (ms) & uptime bot |\n"
            f"| `/stats` | Lihat statistik database bot |\n"
            f"| Pengembang | [Amang](https://github.com/amanqs) (@BukanDevelopers) |\n\n"
            f"| 🤖 Nusantara Stream 🤖 |\n"
            f"|:---:|\n"
            f"| |"
        ),
    }

    # Backward compatibility aliases
    help_texts["music"] = help_texts["play"]
    help_texts["live"] = help_texts["tv"]

    cur_page = 2 if action == "page_2" else 1
    main_help_text = (
        f"| 🤖 Panduan Penggunaan — {Config.BOT_NAME} |\n"
        f"|:---:|\n"
        f"| Pilih kategori menu di bawah (Halaman {cur_page}/2) |\n\n"
        f"| Statistik Sistem | Detail Jumlah |\n"
        f"|:---|:---|\n"
        f"| 📢 Served Chats | `{chats_cnt:,} grup` |\n"
        f"| 👥 Served Users | `{users_cnt:,} pengguna` |\n"
        f"| 🤖 Engine | `Kurigram + PyTgCalls v2.3.3` |\n\n"
        f"| 💡 Klik tombol kategori di bawah untuk membuka panduan: |\n"
        f"|:---:|\n"
        f"| |"
    )

    if action in help_texts:
        selected_text = help_texts[action]
        markup = get_help_keyboard(action)
    else:
        selected_text = main_help_text
        markup = get_help_keyboard("main", page=cur_page)

    try:
        await RichParser.edit(
            query,
            selected_text,
            reply_markup=markup,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
    except Exception:
        pass
    await query.answer()
