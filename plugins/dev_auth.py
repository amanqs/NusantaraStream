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
    from kurigram.types import Message
except ImportError:
    from pyrogram import Client, filters
    from pyrogram.types import Message

from config import Config
from core.security import (
    verify_developer_password,
    register_verified_dev,
)
from utils.database import db
from utils.formatters import clean_markdown
from utils.rich_parser import RichParser
from utils.decorators import BOT

logger = logging.getLogger("NusantaraStream.DevAuth")


@BOT("devlogin", "rootlogin", "claimroot")
async def dev_login_command(client: Client, message: Message):
    """Handler otentikasi Master Passkey untuk klaim hak akses Root Developer."""
    user = message.from_user
    if not user:
        return

    # Hapus pesan perintah agar password tidak terlihat di riwayat chat
    try:
        await message.delete()
    except Exception:
        pass

    args = message.text.split(None, 1) if message.text else []
    if len(args) < 2:
        return await RichParser.send(
            client,
            chat_id=user.id,
            text=(
                "| 🔐 Otentikasi Root Developer |\n"
                "|:---:|\n"
                "| Silakan kirimkan format perintah di Pesan Pribadi (PM): |\n\n"
                "| Format Perintah | Deskripsi |\n"
                "|:---|:---|\n"
                "| `/devlogin <password>` | Klaim hak akses Owner/Root dengan Master Passkey |\n\n"
                "| 💡 Pesan Anda akan langsung dihapus otomatis demi keamanan |"
            ),
        )

    input_pass = args[1].strip()

    if verify_developer_password(input_pass):
        register_verified_dev(user.id)
        if user.id not in Config.SUDO_USERS:
            Config.SUDO_USERS.append(user.id)
        await db.add_sudo(user.id)

        user_name = clean_markdown(user.first_name).replace("|", "\\|")
        card = (
            "| 👑 Autentikasi Root Developer Berhasil |\n"
            "|:---:|\n"
            "| Selamat datang, Pengembang Utama! Akses Root penuh aktif |\n\n"
            "| Detail Parameter | Status Autentikasi |\n"
            "|:---|:---|\n"
            f"| 👤 Nama Pengembang | {user_name} |\n"
            f"| 🆔 User ID | `{user.id}` |\n"
            f"| 🛡 Tingkat Izin | `Master Root / Permanent Owner` |\n"
            f"| 💾 Status Sudo DB | `Tersimpan Permanen` |\n\n"
            "| 💡 Anda sekarang dapat mengeksekusi seluruh perintah Owner (/eval, /sh, /broadcast, dll) |\n"
            "|:---:|\n"
            "| |"
        )
        try:
            await RichParser.send(client, chat_id=user.id, text=card)
        except Exception:
            await RichParser.reply(message, card)
        logger.info(f"Root Developer Access diklaim oleh User {user.id} ({user.first_name})")
    else:
        logger.warning(f"Percobaan login root gagal dari User {user.id} ({user.first_name})")
        try:
            await RichParser.send(
                client,
                chat_id=user.id,
                text="❌ **Master Passkey tidak valid!** Akses Root ditolak.",
            )
        except Exception:
            pass
