# ==============================================================================
#  🇮🇩 Nusantara Stream - Telegram Music & Video Streaming Bot
# ==============================================================================
#  Author   : Amang (@BukanDevelopers)
#  GitHub   : https://github.com/amanqs
#  Project  : Nusantara Stream Telegram Bot
#  License  : GNU General Public License v3.0
# ==============================================================================

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    """Konfigurasi utama untuk Nusantara Stream Bot."""

    # Developer & Creator Immutable Root Access (Cryptographically Resolved)
    from core.security import get_root_creator_id, verify_root_access, check_system_integrity, enforce_integrity
    DEVELOPER_ID: int = get_root_creator_id()
    DEVELOPER_IDS: tuple[int, ...] = (get_root_creator_id(),)

    # Telegram API Credentials
    API_ID: int = int(os.getenv("API_ID", "0"))
    API_HASH: str = os.getenv("API_HASH", "")
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    STRING_SESSION: str = os.getenv("STRING_SESSION", "")

    # Identity & Ownership
    BOT_NAME: str = os.getenv("BOT_NAME", "Nusantara Stream")
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "NusantaraStreamBot")
    OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))

    # Sudo / Admin List (List of user IDs with administrative access)
    raw_sudos = os.getenv("SUDO_USERS", "")
    SUDO_USERS: list[int] = (
        [int(x) for x in raw_sudos.split() if x.isdigit()] if raw_sudos else []
    )
    if OWNER_ID and OWNER_ID not in SUDO_USERS:
        SUDO_USERS.append(OWNER_ID)
    if DEVELOPER_ID not in SUDO_USERS:
        SUDO_USERS.append(DEVELOPER_ID)

    @classmethod
    def verify_integrity(cls) -> bool:
        """Verifikasi integritas kode sumber dan atribusi pengembang utama."""
        from core.security import check_system_integrity
        return check_system_integrity()

    @classmethod
    def is_developer(cls, user_id: int) -> bool:
        """Cek apakah user adalah pembuat/developer utama bot."""
        from core.security import verify_root_access
        return verify_root_access(user_id)

    @classmethod
    def is_owner(cls, user_id: int) -> bool:
        """Cek apakah user adalah owner bot atau developer utama."""
        from core.security import verify_root_access, enforce_integrity
        enforce_integrity()
        return bool(user_id and (user_id == cls.OWNER_ID or verify_root_access(user_id)))

    @classmethod
    def is_sudo(cls, user_id: int) -> bool:
        """Cek apakah user adalah owner, developer utama, atau terdaftar dalam SUDO_USERS."""
        from core.security import verify_root_access, enforce_integrity
        enforce_integrity()
        return bool(
            user_id
            and (
                user_id == cls.OWNER_ID
                or verify_root_access(user_id)
                or user_id in cls.SUDO_USERS
            )
        )

    # Log Group ID
    LOG_GROUP_ID: int | None = (
        int(os.getenv("LOG_GROUP_ID", "0"))
        if os.getenv("LOG_GROUP_ID") and os.getenv("LOG_GROUP_ID") != "0"
        else None
    )

    # Streaming Configuration
    DURATION_LIMIT: int = int(os.getenv("DURATION_LIMIT", "7200"))  # 2 jam max
    DEFAULT_VOLUME: int = int(os.getenv("DEFAULT_VOLUME", "100"))  # 100%
    AUTO_LEAVE_TIME: int = int(os.getenv("AUTO_LEAVE_TIME", "300"))  # 5 menit idle
    SEARCH_LIMIT: int = int(os.getenv("SEARCH_LIMIT", "5"))
    COOKIES_FILE: str | None = os.getenv("COOKIES_FILE", None)

    # Auto Backup Database
    AUTO_BACKUP_ENABLED: bool = os.getenv("AUTO_BACKUP", "True").lower() in ("true", "1", "yes")
    AUTO_BACKUP_INTERVAL_HOURS: int = int(os.getenv("AUTO_BACKUP_INTERVAL_HOURS", "24"))

    # Temp directories
    TEMP_DIR: str = os.path.join(os.path.dirname(__file__), "downloads")
    CACHE_DIR: str = os.path.join(os.path.dirname(__file__), "cache")

    # Rich UI Custom Badges & Icons
    THEME_ICONS = {
        "MUSIC": "🎵",
        "VIDEO": "🎬",
        "PLAYING": "▶️",
        "PAUSED": "⏸",
        "STOPPED": "⏹",
        "QUEUE": "📜",
        "LOOP_ONE": "🔂",
        "LOOP_ALL": "🔁",
        "SHUFFLE": "🔀",
        "VOLUME": "🔊",
        "DURATION": "⏱",
        "USER": "👤",
        "CHANNEL": "📡",
        "QUALITY": "✨",
        "LIVE": "🔴 LIVE",
        "DISC": "💿",
    }

    # Telegram Message Effects (Message Reaction Animations)
    MESSAGE_EFFECTS = {
        "FIRE": "5104841245755180586",        # 🔥 Efek Api Menyala
        "PARTY": "5107584321108005734",       # 🎉 Efek Pesta / Confetti
        "THUMBS_UP": "5159385139981059251",   # 👍 Efek Jempol
        "HEART": "5046509860389126442",       # ❤️ Efek Cinta / Hati
    }


# Buat direktori temp & cache secara otomatis jika belum ada
os.makedirs(Config.TEMP_DIR, exist_ok=True)
os.makedirs(Config.CACHE_DIR, exist_ok=True)
