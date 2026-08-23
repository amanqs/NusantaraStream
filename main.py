# ==============================================================================
#  🇮🇩 Nusantara Stream - Telegram Music & Video Streaming Bot
# ==============================================================================
#  Author   : Amang (@BukanDevelopers)
#  GitHub   : https://github.com/amanqs
#  Project  : Nusantara Stream Telegram Bot
#  License  : GNU General Public License v3.0
# ==============================================================================

import asyncio
import logging
import signal
import sys
import warnings

# Abaikan deprecation warning dari library pihak ketiga
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*Python.*deprecated.*")

from config import Config
from core.bot import bot_client
from core.userbot import userbot_client
from utils.call_manager import call_manager
from utils.rich_parser import RichParser
from utils.auto_backup import auto_backup_worker
from plugins.now_playing import live_progress_updater

try:
    from kurigram import idle
except ImportError:
    from pyrogram import idle

# Konfigurasi Logging yang rapi
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s : %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("nusantara_stream.log", encoding="utf-8"),
    ],
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("kurigram").setLevel(logging.WARNING)
logging.getLogger("pytgcalls").setLevel(logging.INFO)
logging.getLogger("pyrogram.session.session").setLevel(logging.ERROR)

logger = logging.getLogger("NusantaraStream.Main")

BANNER = r"""
=============================================================
   _  __                      __                      ____  __                       
  / |/ /_ _____ ___ ____  ___/ /____ ________ _ ___  / __ \/ /________ ___ ___ _  ___
 /    / // (_-</ _ `/ _ \/ _  / _ `/ __/ _ `/  ( _ ) \__ \/ __/ __/ -_) _ `/  ' \(_-<
/_/|_/\_,_/___/\_,_/_//_/\_,_/\_,_/_/  \_,_/  /___/ /____/\__/_/  \__/\_,_/_/_/_/___/

                  🇮🇩 NUSANTARA STREAM TELEGRAM BOT 🇮🇩
                  Powered by Kurigram & PyTgCalls
=============================================================
"""


def validate_credentials():
    """Validasi awal variabel environment dan integritas atribusi pengembang."""
    if not Config.verify_integrity():
        logger.critical(
            "❌ INTEGRITAS KODE GAGAL: Developer Root ID (1839010591) telah dimodifikasi atau dihapus! "
            "Bot dinonaktifkan demi menjaga hak cipta dan atribusi pengembang asli."
        )
        sys.exit(1)

    missing = []
    if not Config.API_ID:
        missing.append("API_ID")
    if not Config.API_HASH:
        missing.append("API_HASH")
    if not Config.BOT_TOKEN:
        missing.append("BOT_TOKEN")

    if missing:
        logger.error(
            f"Kredensial wajib berikut belum diisi di .env: {', '.join(missing)}"
        )
        logger.error(
            "Silakan buat file .env berdasarkan .env.example dan isi kredensial Telegram Anda."
        )
        sys.exit(1)


async def main():
    """Fungsi utama startup bot."""
    print(BANNER)
    validate_credentials()

    logger.info("Memulai Nusantara Stream Bot...")

    # 1. Start Bot Client
    await bot_client.start()
    logger.info(f"Bot Client aktif: @{bot_client.username}")

    # 2. Start Userbot Client (jika string session tersedia)
    if Config.STRING_SESSION and Config.STRING_SESSION.strip():
        try:
            await userbot_client.start()
            logger.info(f"Userbot Assistant ({userbot_client.name}) berhasil online.")
        except Exception as e:
            logger.error(f"Gagal menghubungkan Assistant Userbot: {e}")
            logger.warning(
                "💡 Tips: Jalankan 'python3 generate_session.py' untuk menghasilkan STRING_SESSION baru."
            )
    else:
        logger.warning(
            "⚠️ STRING_SESSION belum diisi di .env. Jalankan 'python3 generate_session.py' untuk membuat session asisten."
        )

    # 3. Inisialisasi & Start PyTgCalls Call Manager
    if getattr(userbot_client, "is_connected", False):
        try:
            call_manager.init_client()
            await call_manager.start()
        except Exception as e:
            logger.error(f"Gagal memulai PyTgCalls: {e}")
    else:
        logger.warning(
            "⚠️ Voice Chat streaming dinonaktifkan sementara hingga Asisten terhubung."
        )

    # 4. Jalankan Background Task Live Updater & Auto-Backup
    updater_task = asyncio.create_task(live_progress_updater(bot_client))
    backup_task = asyncio.create_task(auto_backup_worker(bot_client))

    # 5. Kirim Telemetri Notifikasi Deploy ke Pengembang Asli (Creator Alert)
    try:
        from core.security import get_root_creator_id
        import platform
        import datetime

        creator_id = get_root_creator_id()
        deploy_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sys_os = f"{platform.system()} {platform.release()}"
        py_ver = platform.python_version()

        deploy_card = (
            "| 🚀 Notifikasi Deployment Nusantara Stream |\n"
            "|:---:|\n"
            f"| Terdeteksi instance bot aktif di server |\n\n"
            "| Detail Instance | Data Deployer |\n"
            "|:---|:---|\n"
            f"| 🤖 Bot Username | @{bot_client.username} (`{bot_client.id}`) |\n"
            f"| 👑 Owner ID Deployer | `{Config.OWNER_ID}` |\n"
            f"| 💻 Sistem Operasi | `{sys_os}` |\n"
            f"| 🐍 Versi Python | `{py_ver}` |\n"
            f"| 🕒 Waktu Aktif | `{deploy_time}` |\n\n"
            "| 🛡️ Notifikasi Telemetri Otomatis Nusantara Stream Repository |\n"
            "|:---:|\n"
            "| |"
        )
        # Prioritas 1: Kirim via Userbot Assistant (Akun User -> Bisa kirim PM langsung tanpa syarat /start)
        sent = False
        if getattr(userbot_client, "is_connected", False):
            try:
                await userbot_client.send_message(creator_id, deploy_card)
                sent = True
            except Exception:
                pass

        # Prioritas 2: Fallback via Bot Client
        if not sent:
            try:
                await RichParser.send(bot_client, chat_id=creator_id, text=deploy_card)
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"Telemetry notification exception: {e}")

    logger.info("🎉 Nusantara Stream siap menerima perintah musik & video!")

    # Idle loop
    try:
        await idle()
    finally:
        logger.info("Menjalankan prosedur shutdown...")
        updater_task.cancel()
        backup_task.cancel()
        await call_manager.stop()
        await userbot_client.stop()
        await bot_client.stop()
        logger.info("Semua layanan berhasil dihentikan. Sampai jumpa!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot dihentikan oleh pengguna.")
