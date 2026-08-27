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
    """Handler perintah /help bergaya Telegram Rich Quote Card."""
    if message.from_user:
        await db.add_served_user(message.from_user.id, message.from_user.first_name, message.from_user.username)
    if message.chat.type.value in ("group", "supergroup", "channel"):
        await db.add_served_chat(message.chat.id, message.chat.title, str(message.chat.type))

    db_stats = await db.get_db_stats()
    users_cnt = db_stats.get("users", 0)
    chats_cnt = db_stats.get("chats", 0)

    help_text = (
        f"| 🤖 Panduan Penggunaan & Perintah {Config.BOT_NAME} |\n"
        f"|:---:|\n"
        f"| Pusat kontrol pemutar musik, video & film Telegram |\n\n"
        f"**📋 Daftar Perintah Utama:**\n"
        f"> • `/play` (judul/link) — Memutar Audio di obrolan suara\n"
        f"> • `/vplay` (judul/link) — Memutar Video HD + Audio di obrolan suara\n"
        f"> • `/film` / `/movie` — Menonton Film bioskop privat di VC\n"
        f"> • `/pause` / `/resume` — Menjeda atau melanjutkan pemutaran\n"
        f"> • `/skip` — Melompati lagu ke antrean berikutnya\n"
        f"> • `/seek` (detik) — Lompat maju / mundur pemutaran media\n"
        f"> • `/queue` — Menampilkan daftar antrean pemutaran\n"
        f"> • `/loop` (1-10) — Mengulang pemutaran media x kali\n"
        f"> • `/settings` — Pengaturan preferensi pemutar grup\n"
        f"> • `/stop` — Menghentikan pemutaran & reset antrean\n\n"
        f"| 📊 Statistik Sistem | Detail Jumlah |\n"
        f"|:---|:---|\n"
        f"| 📢 Served Chats | `{chats_cnt:,} grup` |\n"
        f"| 👥 Served Users | `{users_cnt:,} pengguna` |\n\n"
        f"| 💡 Klik tombol kategori di bawah untuk panduan lengkap spesifik: |\n"
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

    db_stats = await db.get_db_stats()
    users_cnt = db_stats.get("users", 0)
    chats_cnt = db_stats.get("chats", 0)

    help_texts = {
        "music": (
            f"| 🎵 Panduan Musik & Audio — {Config.BOT_NAME} |\n"
            f"|:---:|\n"
            f"| Kontrol pemutaran musik, playlist & antrean di VC |\n\n"
            f"**🎧 Pemutaran & Media:**\n"
            f"> • `/play` (judul/link) — Putar audio YouTube di VC\n"
            f"> • `/play` (balas audio) — Putar berkas audio Telegram\n"
            f"> • `/playforce` (judul) — Putar lagu langsung & lewati antrean\n"
            f"> • `/seek` (detik) / `/ff` / `/rw` — Lompat maju/mundur audio\n"
            f"> • `/song` (judul) — Unduh file MP3 320kbps + Album Art\n"
            f"> • `/lyrics` (judul) — Cari & tampilkan lirik lagu lengkap\n"
            f"> • `/radio` — Putar siaran Radio 24/7 Nasional di VC\n"
            f"> • `/autoplay` (on/off) — Putar rekomendasi otomatis\n\n"
            f"**🎛️ Playlist & Kontrol Player:**\n"
            f"> • `/playlist` / `/myplaylist` — Buka daftar playlist pribadi\n"
            f"> • `/save` (judul/link) — Simpan lagu ke playlist pribadi\n"
            f"> • `/playplaylist` — Putar semua lagu di playlist ke VC\n"
            f"> • `/delplaylist` (nomor) — Hapus lagu tertentu dari playlist\n"
            f"> • `/np` / `/nowplaying` — Tampilkan kartu lagu yang diputar\n"
            f"> • `/queue` / `/q` — Tampilkan daftar antrean lagu saat ini\n"
            f"> • `/shuffle` — Acak urutan lagu di daftar antrean\n"
            f"> • `/loop` (1-10/off) — Putar ulang lagu saat ini x kali\n"
            f"> • `/pause` / `/resume` — Jeda atau lanjutkan pemutaran\n"
            f"> • `/skip` / `/next` — Lewati lagu aktif ke lagu berikutnya\n"
            f"> • `/stop` / `/end` — Hentikan pemutaran & reset antrean\n"
            f"> • `/volume` (1-200) — Atur volume pemutaran musik (100%)\n"
            f"> • `/mute` / `/unmute` — Bisukan atau buka suara asisten di VC\n\n"
            f"| 💡 Gunakan tombol player di bawah kartu untuk kontrol cepat! |\n"
            f"|:---:|\n"
            f"| |"
        ),
        "video": (
            f"| 🎬 Panduan Video, Film & TV — {Config.BOT_NAME} |\n"
            f"|:---:|\n"
            f"| Streaming video 720p HD, bioskop & Live TV di VC |\n\n"
            f"**🎥 Video & Bioskop Film:**\n"
            f"> • `/film` / `/movie` / `/bioskop` — Buka katalog & streaming film\n"
            f"> • `/film` (judul) — Cari & putar film dari channel privat\n"
            f"> • `/seek` (detik) / `/ff` / `/rw` — Lompat maju/mundur video/film\n"
            f"> • `/vplay` (judul/link) — Putar video YouTube 720p di VC\n"
            f"> • `/vplay` (balas video) — Putar berkas file video Telegram\n"
            f"> • `/vplayforce` (judul) — Putar video langsung & lewati antrean\n\n"
            f"**📺 Live TV & Downloader:**\n"
            f"> • `/tv` / `/iptv` — Menu Live TV & remote ganti channel\n"
            f"> • `/tv` (link m3u8) — Putar siaran IPTV/HLS kustom di VC\n"
            f"> • `/video` (judul) — Unduh video HD 720p MP4 ke chat\n\n"
            f"| 💡 Kontrol seek -30s/-10s/+10s/+30s tersedia di panel video! |\n"
            f"|:---:|\n"
            f"| |"
        ),
        "effects": (
            f"| ⚡ Panduan Efek Audio & Kecepatan — {Config.BOT_NAME} |\n"
            f"|:---:|\n"
            f"| Modifikasi tempo & efek suara secara realtime di VC |\n\n"
            f"**🎚️ Perintah Efek Suara:**\n"
            f"> • `/speed` (0.5-2.0) — Ubah tempo/kecepatan lagu presisi\n"
            f"> • `/nightcore` — Efek nada tinggi & tempo cepat (1.25x)\n"
            f"> • `/slowed` — Efek santai tempo lambat (0.85x)\n"
            f"> • `/bass` / `/bassboost` — Efek penguat bass frekuensi rendah\n"
            f"> • `/speed 1.0` — Kembalikan tempo pemutaran ke normal\n\n"
            f"| 🤖 Nusantara Stream 🤖 |\n"
            f"|:---:|\n"
            f"| |"
        ),
        "admin": (
            f"| 🛡️ Panduan Admin Grup — {Config.BOT_NAME} |\n"
            f"|:---:|\n"
            f"| Pengaturan hak akses & preferensi pemutar grup |\n\n"
            f"**⚙️ Perintah Otorisasi & Pengaturan:**\n"
            f"> • `/settings` — Panel konfigurasi preferensi grup interaktif\n"
            f"> • `/auth` (reply/id) — Beri izin member non-admin kontrol\n"
            f"> • `/unauth` (reply/id) — Cabut izin kontrol member dari grup\n"
            f"> • `/authlist` — Tampilkan daftar user terotorisasi di grup\n\n"
            f"| ℹ️ Peminta lagu otomatis memiliki hak kontrol media miliknya |\n"
            f"|:---:|\n"
            f"| |"
        ),
        "sudo": (
            f"| 👑 Panduan Sudo & Owner — {Config.BOT_NAME} |\n"
            f"|:---:|\n"
            f"| Akses kontrol level pengembang & pemilik sistem bot |\n\n"
            f"**⚙️ Manajemen Server & Bot:**\n"
            f"> • `/broadcast` — Kirim pesan broadcast ke semua user & grup\n"
            f"> • `/activevc` — Cek seluruh Voice Chat aktif yang berjalan\n"
            f"> • `/clean` — Bersihkan berkas cache sementara di server\n"
            f"> • `/sysinfo` — Tampilkan statistik CPU, RAM, Disk & Server\n"
            f"> • `/sudolist` — Tampilkan daftar seluruh Sudo Admin & Owner\n"
            f"> • `/reload` — (Hot Reload) Muat ulang kode tanpa restart bot\n"
            f"> • `/restart` — Restart bot secara aman & otomatis reconnect\n"
            f"> • `/logs` — Unduh berkas log bot untuk diagnosa sistem\n\n"
            f"**🗄️ Database & Akses Owner:**\n"
            f"> • `/backup` — (Owner) Unduh berkas cadangan database SQLite\n"
            f"> • `/autobackup` — (Owner) Panel konfigurasi backup harian\n"
            f"> • `/restore` — (Owner) Pulihkan database dari file .db (reply)\n"
            f"> • `/addsudo` (id/user) — (Owner) Tambah Sudo Admin baru\n"
            f"> • `/delsudo` (id/user) — (Owner) Hapus Sudo Admin dari sistem\n"
            f"> • `/eval` (kode) — (Owner) Eksekusi potongan kode Python\n"
            f"> • `/sh` (perintah) — (Owner) Jalankan perintah shell Linux\n\n"
            f"| 🤖 Nusantara Stream 🤖 |\n"
            f"|:---:|\n"
            f"| |"
        ),
        "info": (
            f"| ℹ️ Informasi Sistem & Statistik — {Config.BOT_NAME} |\n"
            f"|:---:|\n"
            f"| Detail status operasional dan engine bot |\n\n"
            f"**📌 Perintah Informasi:**\n"
            f"> • `/start` — Tampilkan pesan sambutan & menu utama\n"
            f"> • `/help` — Buka pusat panduan & menu bantuan interaktif\n"
            f"> • `/ping` — Cek kecepatan respon (latensi ms) & uptime\n"
            f"> • `/stats` — Lihat statistik database user & grup terdaftar\n"
            f"> • 👨‍💻 **Pengembang**: [Amang](https://github.com/amanqs) (@BukanDevelopers)\n\n"
            f"| 🤖 Engine: Kurigram + PyTgCalls v2.3.3 |\n"
            f"|:---:|\n"
            f"| |"
        ),
    }

    main_help_text = (
        f"| 🤖 Panduan Penggunaan & Perintah {Config.BOT_NAME} |\n"
        f"|:---:|\n"
        f"| Pusat kontrol pemutar musik, video & film Telegram |\n\n"
        f"**📋 Daftar Perintah Utama:**\n"
        f"> • `/play` (judul/link) — Memutar Audio di obrolan suara\n"
        f"> • `/vplay` (judul/link) — Memutar Video HD + Audio di obrolan suara\n"
        f"> • `/film` / `/movie` — Menonton Film bioskop privat di VC\n"
        f"> • `/pause` / `/resume` — Menjeda atau melanjutkan pemutaran\n"
        f"> • `/skip` — Melompati lagu ke antrean berikutnya\n"
        f"> • `/seek` (detik) — Lompat maju / mundur pemutaran media\n"
        f"> • `/queue` — Menampilkan daftar antrean pemutaran\n"
        f"> • `/loop` (1-10) — Mengulang pemutaran media x kali\n"
        f"> • `/settings` — Pengaturan preferensi pemutar grup\n"
        f"> • `/stop` — Menghentikan pemutaran & reset antrean\n\n"
        f"| 📊 Statistik Sistem | Detail Jumlah |\n"
        f"|:---|:---|\n"
        f"| 📢 Served Chats | `{chats_cnt:,} grup` |\n"
        f"| 👥 Served Users | `{users_cnt:,} pengguna` |\n\n"
        f"| 💡 Klik tombol kategori di bawah untuk panduan lengkap spesifik: |\n"
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
