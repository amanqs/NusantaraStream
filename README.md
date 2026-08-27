# 🎵 Nusantara Stream (@NusantaraStreamBot)

> **Bot Pemutar Musik & Video Telegram Modern Berbasis Kurigram & PyTgCalls**

---

## 🌟 Fitur Utama

- 🚀 **Engine Modern & Cepat:** Dibangun dengan library **Kurigram** (asynchronous modern MTProto client) & **PyTgCalls**.
- 🎶 **Kualitas Audio & Video HD:** Mendukung streaming audio beresolusi tinggi (320kbps) dan video hingga 720p HD.
- 🎛 **Interactive Control Panel:** Keyboard inline interaktif 3 baris (Play/Pause, Skip, Stop, Shuffle, Loop, Volume +/-).
- 🔍 **Top-5 Interactive Search:** Menampilkan pilihan 5 lagu teratas dengan tombol nomor interaktif sebelum memutar lagu.
- 📊 **Visual Progress Bar:** Menampilkan visualizer durasi berjalan `[🔘═══════════]` secara real-time dan aman dari FloodWait.
- ⚡ **Non-Blocking Architecture:** Ekstraksi yt-dlp menggunakan thread executor `asyncio` agar bot tetap responsif melayani banyak grup bersamaan.
- 🔁 **Loop & Shuffle Management:** Fitur perulangan lagu serta pengacakan antrean yang fleksibel.
- 🛡 **Sistem Otorisasi Multi-Level:** Perlindungan hak akses untuk Admin Grup, Pengguna Terotorisasi (`/auth`), dan Pemilik Bot (`SUDO_USERS`).

---

## 📂 Struktur Proyek

```
NusantaraStream/
├── config.py                 # Konfigurasi Environment & Token
├── main.py                   # Entry point aplikasi & startup PyTgCalls
├── requirements.txt          # Daftar dependensi Python
├── .env.example              # Template variabel environment
├── Dockerfile                # Image container dengan FFMPEG
├── docker-compose.yml        # Runner multi-container
├── core/
│   ├── __init__.py
│   ├── bot.py                # Client Kurigram Bot
│   └── userbot.py            # Client Assistant (Userbot)
├── utils/
│   ├── __init__.py
│   ├── call_manager.py       # Wrapper PyTgCalls & event stream ended
│   ├── formatters.py         # Visual progress bar & Rich HTML template
│   ├── keyboards.py          # Interactive Inline Keyboards
│   ├── queue.py              # Manajer antrean lagu & loop
│   ├── ytdl.py               # Extractor audio/video yt-dlp asinkron
│   └── decorators.py         # Proteksi hak admin & otorisasi
└── plugins/
    ├── __init__.py
    ├── start.py              # /start, /help, /ping
    ├── play.py               # /play, /vplay, top-5 search callback
    ├── controls.py           # /pause, /resume, /skip, /stop, /queue, dll
    ├── now_playing.py        # /np, live progress updater
    └── admin.py              # /auth, /unauth, /activevc, /clean
```

---

## 🛠 Panduan Instalasi & Menjalankan Bot

### 1. Prasyarat Sistem
- **Python 3.11+** (atau minimal Python 3.10)
- **FFmpeg** (Wajib terpasang di sistem operasi):
  ```bash
  # Ubuntu / Debian
  sudo apt update && sudo apt install ffmpeg -y

  # macOS (Homebrew)
  brew install ffmpeg

  # Windows (Chocolatey)
  choco install ffmpeg
  ```

### 2. Kloning & Pengaturan Lingkungan
```bash
# Masuk ke direktori proyek
cd NusantaraStream

# Buat virtual environment (opsional tapi disarankan)
python3 -m venv venv
source venv/bin/activate  # Untuk Linux/macOS
# venv\Scripts\activate   # Untuk Windows

# Pasang dependensi
pip install -U pip setuptools wheel
pip install -r requirements.txt
```

### 3. Konfigurasi Variabel Lingkungan (`.env`)
Salin file template `.env.example` menjadi `.env`:
```bash
cp .env.example .env
```

Buka file `.env` dan isi variabel berikut:
```env
# Dapatkan dari https://my.telegram.org
API_ID=12345678
API_HASH=abcdef1234567890abcdef1234567890

# Dapatkan dari @BotFather di Telegram
BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ

# Dapatkan session string akun asisten (Pyrogram Session)
STRING_SESSION=BQAF...

# User ID Telegram Anda (dapatkan dari @userinfobot)
OWNER_ID=123456789
```

> **💡 Cara Mendapatkan Pyrogram / Kurigram String Session:**
> Cukup jalankan script interaktif bawaan:
> ```bash
> python3 generate_session.py
> ```
> Masukkan nomor telepon akun asisten (+628...), masukkan kode OTP Telegram, dan script akan otomatis menyimpan `STRING_SESSION` ke file `.env`.

### 4. Menjalankan Bot
```bash
python3 main.py
```

---

## 🐳 Menjalankan dengan Docker

```bash
# Build dan jalankan di background
docker-compose up -d --build

# Melihat log bot
docker-compose logs -f
```

---

## 📜 Daftar Perintah Bot

| Perintah | Deskripsi |
| :--- | :--- |
| `/start` | Membuka pesan sambutan dan tombol navigasi interaktif. |
| `/help` | Menampilkan panduan dan seluruh daftar perintah. |
| `/ping` | Mengecek latensi respon bot dan uptime server. |
| `/play [judul/link]` | Memutar musik audio di Voice Chat grup. |
| `/vplay [judul/link]` | Memutar video streaming di Voice Chat grup. |
| `/tv` atau `/iptv` | Buka menu Siaran Live TV & IPTV Indonesia 24/7 di VC. |
| `/pause` | Menjeda pemutaran musik saat ini. |
| `/resume` | Melanjutkan kembali lagu yang sedang dijeda. |
| `/skip` atau `/next` | Melompati lagu saat ini dan memutar lagu berikutnya. |
| `/stop` atau `/end` | Menghentikan lagu, membersihkan antrean, dan keluar VC. |
| `/queue` atau `/q` | Melihat daftar lagu yang sedang mengantre. |
| `/np` atau `/nowplaying` | Menampilkan kartu lagu saat ini beserta progress bar live. |
| `/volume [1-200]` | Mengatur volume output suara. |
| `/loop` | Mengaktifkan/menonaktifkan perulangan lagu saat ini. |
| `/shuffle` | Mengacak urutan antrean lagu yang tersisa. |
| `/auth` | Memberikan hak akses kontrol bot kepada anggota grup. |
| `/unauth` | Mencabut hak akses khusus anggota grup. |
| `/authlist` | Melihat daftar anggota yang memiliki akses khusus. |
| `/activevc` | `[Sudo]` Melihat daftar grup yang sedang aktif memutar lagu. |
| `/clean` | `[Sudo]` Membersihkan cache dan file temporary server. |

## 👑 Pengembang & Kontributor (Credits)

- **Lead Developer**: [Amang](https://github.com/amanqs)
- **Telegram Channel / Support**: [@BukanDevelopers](https://t.me/BukanDevelopers)
- **GitHub Repository**: [github.com/amanqs](https://github.com/amanqs)

---

## 📄 Lisensi
Didistribusikan di bawah Lisensi GNU General Public License v3.0 (GPL-3.0). Dibuat dengan ❤️ untuk komunitas Telegram Nusantara.
