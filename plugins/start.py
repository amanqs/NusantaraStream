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
    """Handler perintah /help bergaya Telegram Rich Message Table Card."""
    if message.from_user:
        await db.add_served_user(message.from_user.id, message.from_user.first_name, message.from_user.username)
    if message.chat.type.value in ("group", "supergroup", "channel"):
        await db.add_served_chat(message.chat.id, message.chat.title, str(message.chat.type))

    help_text = (
        f"| 🤖 Pusat Panduan & Menu Bantuan {Config.BOT_NAME} |\n"
        f"|:---:|\n"
        f"| Pilih kategori menu bantuan di bawah untuk melihat daftar perintah lengkap |\n\n"
        f"| Kategori Menu | Isi Cakupan Perintah |\n"
        f"|:---|:---|\n"
        f"| 🎵 Musik & Audio | Pemutaran lagu, antrean, lirik & radio |\n"
        f"| 🎬 Video Stream | Pemutaran video 720p HD & siaran live IPTV |\n"
        f"| ⚡ Efek Audio | Pengaturan tempo, nightcore, slowed & bass |\n"
        f"| 🛡️ Admin Grup | Mode otorisasi member & preferensi grup |\n"
        f"| 👑 Sudo & Owner | Broadcast, manajemen server, log & sudo |\n"
        f"| ℹ️ Info Sistem | Cek ping, uptime bot & statistik server |\n\n"
        f"| 💡 Klik tombol kategori di bawah untuk membuka panduan spesifik: |\n"
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
        f"| 👥 Pengguna Terdaftar | `{users_cnt:,}` pengguna |\n"
        f"| 📢 Grup Terlayani | `{chats_cnt:,}` grup |\n"
        f"| 🤖 Engine | Kurigram + PyTgCalls v2.3.3 |\n\n"
        f"| 🤖 Nusantara Stream 🤖 |\n"
        f"|:---:|\n"
        f"| |"
    )
    await RichParser.edit(reply, text)


@Client.on_callback_query(filters.regex(r"^help:(.+)"))
async def help_callback_handler(client: Client, query: CallbackQuery):
    """Handler navigasi tab bantuan via callback inline dengan Rich Markdown Table Card."""
    action = query.data.split(":")[1]

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

    help_texts = {
        "music": (
            "| 🎵 Panduan Perintah Musik & Audio |\n"
            "|:---:|\n"
            "| Kontrol lengkap pemutaran audio di Voice Chat |\n\n"
            "| Perintah | Deskripsi & Format Penggunaan |\n"
            "|:---|:---|\n"
            "| `/play <judul/link>` | Putar audio YouTube di obrolan suara |\n"
            "| `/play` (balas audio) | Putar file berkas audio dari Telegram |\n"
            "| `/playforce <judul>` | Putar lagu langsung & lewati antrean |\n"
            "| `/save [judul/link]` | Simpan lagu ke playlist pribadi |\n"
            "| `/playlist` / `/myplaylist` | Buka daftar playlist lagu pribadi |\n"
            "| `/playplaylist` / `/playpl` | Putar semua lagu di playlist ke VC |\n"
            "| `/delplaylist <nomor>` | Hapus lagu tertentu dari playlist |\n"
            "| `/song <judul>` | Unduh file MP3 320kbps + Album Art |\n"
            "| `/lyrics [judul]` | Cari & tampilkan lirik lagu lengkap |\n"
            "| `/radio` | Putar siaran Radio 24/7 Nasional di VC |\n"
            "| `/autoplay [on/off]` | Putar lagu rekomendasi otomatis tanpa henti |\n"
            "| `/np` / `/nowplaying` | Tampilkan kartu lagu yang sedang diputar |\n"
            "| `/queue` / `/q` | Tampilkan daftar antrean lagu saat ini |\n"
            "| `/shuffle` | Acak urutan lagu di daftar antrean |\n"
            "| `/loop <1-10/off>` | Putar ulang lagu saat ini x kali |\n"
            "| `/pause` / `/resume` | Jeda atau lanjutkan pemutaran musik |\n"
            "| `/skip` / `/next` | Lewati lagu aktif ke lagu berikutnya |\n"
            "| `/stop` / `/end` | Hentikan pemutaran & hapus antrean |\n"
            "| `/volume [1-200]` | Atur volume pemutaran musik (default: 100%) |\n"
            "| `/mute` / `/unmute` | Bisukan atau aktifkan suara asisten di VC |\n\n"
            "| 🤖 Nusantara Stream 🤖 |\n"
            "|:---:|\n"
            "| |"
        ),
        "video": (
            "| 🎬 Panduan Perintah Video & Live Stream |\n"
            "|:---:|\n"
            "| Pemutaran video berkualitas HD dan siaran langsung |\n\n"
            "| Perintah | Deskripsi & Format Penggunaan |\n"
            "|:---|:---|\n"
            "| `/vplay <judul/link>` | Putar video YouTube 720p di Voice Chat |\n"
            "| `/vplay` (balas video) | Putar file berkas video dari Telegram |\n"
            "| `/vplayforce <judul>` | Putar video langsung & lewati antrean |\n"
            "| `/tv` / `/iptv` | Buka menu Siaran Live TV Indonesia 24/7 di VC |\n"
            "| `/tv <link m3u8>` | Putar siaran langsung IPTV/HLS kustom di VC |\n"
            "| `/video <judul>` | Unduh video HD 720p MP4 ke chat |\n\n"
            "| 🤖 Nusantara Stream 🤖 |\n"
            "|:---:|\n"
            "| |"
        ),
        "effects": (
            "| ⚡ Panduan Efek Audio & Kecepatan |\n"
            "|:---:|\n"
            "| Modifikasi audio secara realtime di Voice Chat |\n\n"
            "| Perintah | Deskripsi & Format Penggunaan |\n"
            "|:---|:---|\n"
            "| `/speed [0.5-2.0]` | Ubah kecepatan/tempo lagu secara presisi |\n"
            "| `/nightcore` | Efek nada tinggi & tempo cepat (1.25x) |\n"
            "| `/slowed` | Efek santai tempo lambat (0.85x) |\n"
            "| `/bass` / `/bassboost` | Efek penguat bass frekuensi rendah maksimal |\n"
            "| `/speed 1.0` | Kembalikan tempo pemutaran ke normal |\n\n"
            "| 🤖 Nusantara Stream 🤖 |\n"
            "|:---:|\n"
            "| |"
        ),
        "admin": (
            "| 🛡️ Panduan Admin Grup & Otorisasi |\n"
            "|:---:|\n"
            "| Pengaturan hak akses & preferensi pemutar grup |\n\n"
            "| Perintah | Deskripsi & Format Penggunaan |\n"
            "|:---|:---|\n"
            "| `/settings` | Panel konfigurasi preferensi grup interaktif |\n"
            "| `/auth [reply/id]` | Beri izin member non-admin mengontrol bot |\n"
            "| `/unauth [reply/id]` | Cabut izin kontrol member dari grup |\n"
            "| `/authlist` | Tampilkan daftar user terotorisasi di grup |\n\n"
            "| 🤖 Nusantara Stream 🤖 |\n"
            "|:---:|\n"
            "| |"
        ),
        "sudo": (
            "| 👑 Panduan Perintah Sudo & Owner |\n"
            "|:---:|\n"
            "| Akses kontrol level pengembang & pemilik bot |\n\n"
            "| Perintah | Deskripsi & Format Penggunaan |\n"
            "|:---|:---|\n"
            "| `/broadcast` | Kirim broadcast ke semua user & grup |\n"
            "| `/activevc` | Cek seluruh Voice Chat aktif yang sedang berjalan |\n"
            "| `/clean` | Bersihkan berkas cache sementara di server |\n"
            "| `/sysinfo` | Tampilkan statistik CPU, RAM, Disk & Server |\n"
            "| `/sudolist` | Tampilkan daftar seluruh Sudo Admin & Owner |\n"
            "| `/reload` | [Hot Reload] Muat ulang kode tanpa restart bot |\n"
            "| `/restart` | Restart bot secara aman & otomatis reconnect |\n"
            "| `/logs` | Unduh berkas log bot untuk diagnosa |\n"
            "| `/backup` | [Owner] Unduh berkas cadangan database SQLite |\n"
            "| `/autobackup` | [Owner] Panel konfigurasi backup otomatis harian |\n"
            "| `/restore` | [Owner] Pulihkan database dari file .db (reply) |\n"
            "| `/addsudo [id/user]` | [Owner] Tambah Sudo Admin baru |\n"
            "| `/delsudo [id/user]` | [Owner] Hapus Sudo Admin dari sistem |\n"
            "| `/eval [kode]` | [Owner] Eksekusi potongan kode Python |\n"
            "| `/sh [perintah]` | [Owner] Jalankan perintah shell Linux |\n\n"
            "| 🤖 Nusantara Stream 🤖 |\n"
            "|:---:|\n"
            "| |"
        ),
        "info": (
            "| ℹ️ Informasi Sistem & Statistik Bot |\n"
            "|:---:|\n"
            "| Detail status operasional dan engine bot |\n\n"
            "| Perintah | Deskripsi & Format Penggunaan |\n"
            "|:---|:---|\n"
            "| `/start` | Tampilkan pesan sambutan & menu utama |\n"
            "| `/help` | Buka pusat panduan & menu bantuan interaktif |\n"
            "| `/ping` | Cek kecepatan respon (latensi ms) & uptime |\n"
            "| `/stats` | Lihat statistik database user & grup terdaftar |\n"
            "| 👨‍💻 Pengembang | [Amang](https://github.com/amanqs) (@BukanDevelopers) |\n\n"
            "| 🤖 Nusantara Stream 🤖 |\n"
            "|:---:|\n"
            "| |"
        ),
    }

    main_help_text = (
        f"| 🤖 Pusat Panduan & Menu Bantuan {Config.BOT_NAME} |\n"
        f"|:---:|\n"
        f"| Pilih kategori menu bantuan di bawah untuk melihat daftar perintah lengkap |\n\n"
        f"| Kategori Menu | Isi Cakupan Perintah |\n"
        f"|:---|:---|\n"
        f"| 🎵 Musik & Audio | Pemutaran lagu, antrean, lirik & radio |\n"
        f"| 🎬 Video Stream | Pemutaran video 720p HD & siaran live IPTV |\n"
        f"| ⚡ Efek Audio | Pengaturan tempo, nightcore, slowed & bass |\n"
        f"| 🛡️ Admin Grup | Mode otorisasi member & preferensi grup |\n"
        f"| 👑 Sudo & Owner | Broadcast, manajemen server, log & sudo |\n"
        f"| ℹ️ Info Sistem | Cek ping, uptime bot & statistik server |\n\n"
        f"| 💡 Klik tombol kategori di bawah untuk membuka panduan spesifik: |\n"
        f"|:---:|\n"
        f"| |"
    )

    selected_text = help_texts.get(action, main_help_text)
    markup = get_help_keyboard(action)
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
