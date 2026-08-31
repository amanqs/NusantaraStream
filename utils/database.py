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
import os
import shutil
import sqlite3
from typing import Any, Optional

from config import Config

logger = logging.getLogger("NusantaraStream.Database")

# Dedicated database directory
DB_DIR = getattr(Config, "DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"))
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = getattr(Config, "DB_PATH", os.path.join(DB_DIR, "nusantara_data.db"))

# Migrasi otomatis jika database sebelumnya tersimpan di direktori cache
_old_cache_dir = getattr(Config, "CACHE_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache"))
_old_cache_db = os.path.join(_old_cache_dir, "nusantara_data.db")
if os.path.exists(_old_cache_db) and not os.path.exists(DB_PATH):
    try:
        shutil.move(_old_cache_db, DB_PATH)
        logger.info(f"Database berhasil dipindahkan dari cache ke folder tersendiri: {DB_PATH}")
        _old_cache_db_old = f"{_old_cache_db}.old"
        if os.path.exists(_old_cache_db_old) and not os.path.exists(f"{DB_PATH}.old"):
            shutil.move(_old_cache_db_old, f"{DB_PATH}.old")
    except Exception as _e:
        logger.warning(f"Gagal memindahkan database dari cache ke folder data: {_e}")


class Database:
    """Manajer SQLite database asinkron untuk menyimpan data user dan grup yang dilayani."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._gban_cache: set[int] = set()
        self._init_db()
        self._load_gban_cache()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Inisialisasi tabel database jika belum ada."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS served_users (
                        user_id INTEGER PRIMARY KEY,
                        first_name TEXT,
                        username TEXT,
                        joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS served_chats (
                        chat_id INTEGER PRIMARY KEY,
                        title TEXT,
                        chat_type TEXT,
                        joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sudo_users (
                        user_id INTEGER PRIMARY KEY,
                        added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS chat_settings (
                        chat_id INTEGER PRIMARY KEY,
                        auth_mode TEXT DEFAULT 'everyone',
                        default_volume INTEGER DEFAULT 100,
                        auto_leave_time INTEGER DEFAULT 300,
                        autoplay INTEGER DEFAULT 0
                    )
                    """
                )
                try:
                    cursor.execute("ALTER TABLE chat_settings ADD COLUMN autoplay INTEGER DEFAULT 0")
                except Exception:
                    pass

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS playlists (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        track_id TEXT,
                        title TEXT,
                        url TEXT,
                        duration INTEGER,
                        channel TEXT,
                        thumbnail TEXT,
                        added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS system_metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS gban_users (
                        user_id INTEGER PRIMARY KEY,
                        first_name TEXT,
                        username TEXT,
                        reason TEXT,
                        banned_by INTEGER,
                        banned_by_name TEXT,
                        banned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                from core.security import get_root_creator_id
                cursor.execute(
                    "INSERT OR IGNORE INTO sudo_users (user_id) VALUES (?)",
                    (get_root_creator_id(),),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Gagal menginisialisasi database: {e}")

    def _load_gban_cache(self):
        """Memuat daftar User ID GBan ke in-memory cache untuk performa instan."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM gban_users")
                rows = cursor.fetchall()
                self._gban_cache = {int(r["user_id"]) for r in rows}
        except Exception as e:
            logger.debug(f"Gagal memuat gban cache: {e}")
            self._gban_cache = set()

    async def add_served_user(
        self, user_id: int, first_name: str = "", username: str = ""
    ) -> bool:
        """Menambahkan atau memperbarui user yang dilayani."""
        if not user_id:
            return False
        loop = asyncio.get_running_loop()

        def _query():
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO served_users (user_id, first_name, username)
                        VALUES (?, ?, ?)
                        ON CONFLICT(user_id) DO UPDATE SET
                            first_name=excluded.first_name,
                            username=excluded.username
                        """,
                        (user_id, first_name or "", username or ""),
                    )
                    conn.commit()
                return True
            except Exception as e:
                logger.debug(f"add_served_user error: {e}")
                return False

        return await loop.run_in_executor(None, _query)

    async def add_served_chat(
        self, chat_id: int, title: str = "", chat_type: str = ""
    ) -> bool:
        """Menambahkan atau memperbarui grup/channel yang dilayani."""
        if not chat_id:
            return False
        loop = asyncio.get_running_loop()

        def _query():
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO served_chats (chat_id, title, chat_type)
                        VALUES (?, ?, ?)
                        ON CONFLICT(chat_id) DO UPDATE SET
                            title=excluded.title,
                            chat_type=excluded.chat_type
                        """,
                        (chat_id, title or "", chat_type or ""),
                    )
                    conn.commit()
                return True
            except Exception as e:
                logger.debug(f"add_served_chat error: {e}")
                return False

        return await loop.run_in_executor(None, _query)

    async def get_served_users(self) -> list[int]:
        """Mengambil daftar seluruh user_id yang terdaftar."""
        loop = asyncio.get_running_loop()

        def _query():
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT user_id FROM served_users")
                    rows = cursor.fetchall()
                    return [r["user_id"] for r in rows]
            except Exception as e:
                logger.error(f"get_served_users error: {e}")
                return []

        return await loop.run_in_executor(None, _query)

    async def get_served_chats(self) -> list[int]:
        """Mengambil daftar seluruh chat_id (grup) yang terdaftar."""
        loop = asyncio.get_running_loop()

        def _query():
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT chat_id FROM served_chats")
                    rows = cursor.fetchall()
                    return [r["chat_id"] for r in rows]
            except Exception as e:
                logger.error(f"get_served_chats error: {e}")
                return []

        return await loop.run_in_executor(None, _query)

    async def remove_served_user(self, user_id: int) -> bool:
        """Menghapus user (misal jika user telah memblokir bot)."""
        loop = asyncio.get_running_loop()

        def _query():
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM served_users WHERE user_id = ?", (user_id,))
                    conn.commit()
                return True
            except Exception as e:
                logger.debug(f"remove_served_user error: {e}")
                return False

        return await loop.run_in_executor(None, _query)

    async def remove_served_chat(self, chat_id: int) -> bool:
        """Menghapus grup (misal jika bot telah di-kick)."""
        loop = asyncio.get_running_loop()

        def _query():
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM served_chats WHERE chat_id = ?", (chat_id,))
                    conn.commit()
                return True
            except Exception as e:
                logger.debug(f"remove_served_chat error: {e}")
                return False

        return await loop.run_in_executor(None, _query)

    async def get_db_stats(self) -> dict[str, int]:
        """Mengambil total statistik user dan grup."""
        loop = asyncio.get_running_loop()

        def _query():
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM served_users")
                    users_count = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM served_chats")
                    chats_count = cursor.fetchone()[0]
                    return {
                        "users": users_count,
                        "chats": chats_count,
                        "total": users_count + chats_count,
                    }
            except Exception as e:
                logger.error(f"get_db_stats error: {e}")
                return {"users": 0, "chats": 0, "total": 0}

        return await loop.run_in_executor(None, _query)

    async def add_sudo(self, user_id: int) -> bool:
        """Menambahkan user ke daftar sudo di database."""
        if not user_id:
            return False
        loop = asyncio.get_running_loop()

        def _query():
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT OR IGNORE INTO sudo_users (user_id) VALUES (?)",
                        (user_id,),
                    )
                    conn.commit()
                return True
            except Exception as e:
                logger.error(f"add_sudo error: {e}")
                return False

        return await loop.run_in_executor(None, _query)

    async def remove_sudo(self, user_id: int) -> bool:
        """Menghapus user dari daftar sudo di database."""
        loop = asyncio.get_running_loop()

        def _query():
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "DELETE FROM sudo_users WHERE user_id = ?",
                        (user_id,),
                    )
                    conn.commit()
                return True
            except Exception as e:
                logger.error(f"remove_sudo error: {e}")
                return False

        return await loop.run_in_executor(None, _query)

    async def get_sudos(self) -> list[int]:
        """Mengambil seluruh daftar sudo_users dari database."""
        from core.security import get_root_creator_id
        loop = asyncio.get_running_loop()

        def _query():
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT user_id FROM sudo_users")
                    rows = cursor.fetchall()
                    ids = [r["user_id"] for r in rows]
                    root_id = get_root_creator_id()
                    if root_id not in ids:
                        ids.append(root_id)
                    return ids
            except Exception as e:
                logger.error(f"get_sudos error: {e}")
                return [get_root_creator_id()]

        return await loop.run_in_executor(None, _query)

    # ------------------------------------------------------------------ #
    #  Global Ban (GBan) Methods                                         #
    # ------------------------------------------------------------------ #

    async def add_gban_user(
        self,
        user_id: int,
        first_name: str = "",
        username: str = "",
        reason: str = "",
        banned_by: int = 0,
        banned_by_name: str = "",
    ) -> bool:
        """Menambahkan pengguna ke daftar Global Ban (GBan)."""
        if not user_id:
            return False
        loop = asyncio.get_running_loop()

        def _query():
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO gban_users (user_id, first_name, username, reason, banned_by, banned_by_name, banned_date)
                        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(user_id) DO UPDATE SET
                            first_name = excluded.first_name,
                            username = excluded.username,
                            reason = excluded.reason,
                            banned_by = excluded.banned_by,
                            banned_by_name = excluded.banned_by_name,
                            banned_date = CURRENT_TIMESTAMP
                        """,
                        (
                            user_id,
                            first_name or "",
                            username or "",
                            reason or "Tidak ada alasan spesifik",
                            banned_by or 0,
                            banned_by_name or "",
                        ),
                    )
                    conn.commit()
                self._gban_cache.add(user_id)
                return True
            except Exception as e:
                logger.error(f"add_gban_user error for {user_id}: {e}")
                return False

        return await loop.run_in_executor(None, _query)

    async def remove_gban_user(self, user_id: int) -> bool:
        """Menghapus pengguna dari daftar Global Ban (GBan)."""
        if not user_id:
            return False
        loop = asyncio.get_running_loop()

        def _query():
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM gban_users WHERE user_id = ?", (user_id,))
                    conn.commit()
                self._gban_cache.discard(user_id)
                return True
            except Exception as e:
                logger.error(f"remove_gban_user error for {user_id}: {e}")
                return False

        return await loop.run_in_executor(None, _query)

    def is_user_gbanned(self, user_id: int) -> bool:
        """Cek apakah user_id berstatus Global Banned (GBan) via in-memory cache."""
        if not user_id:
            return False
        return user_id in self._gban_cache

    async def get_gban_user(self, user_id: int) -> Optional[dict]:
        """Mengambil data detail pengguna yang di-GBan."""
        if not user_id:
            return None
        loop = asyncio.get_running_loop()

        def _query():
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM gban_users WHERE user_id = ?", (user_id,))
                    row = cursor.fetchone()
                    return dict(row) if row else None
            except Exception as e:
                logger.error(f"get_gban_user error for {user_id}: {e}")
                return None

        return await loop.run_in_executor(None, _query)

    async def get_gban_users(self) -> list[dict]:
        """Mengambil seluruh daftar pengguna yang terkena GBan."""
        loop = asyncio.get_running_loop()

        def _query():
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM gban_users ORDER BY banned_date DESC")
                    rows = cursor.fetchall()
                    return [dict(r) for r in rows]
            except Exception as e:
                logger.error(f"get_gban_users error: {e}")
                return []

        return await loop.run_in_executor(None, _query)

    async def get_gban_count(self) -> int:
        """Mengambil total jumlah pengguna yang di-GBan."""
        return len(self._gban_cache)

    async def get_metadata(self, key: str, default: str = "") -> str:
        """Mengambil nilai metadata sistem berdasarkan key."""
        loop = asyncio.get_running_loop()

        def _query():
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT value FROM system_metadata WHERE key = ?", (key,))
                    row = cursor.fetchone()
                    return row["value"] if row else default
            except Exception as e:
                logger.error(f"get_metadata error for {key}: {e}")
                return default

        return await loop.run_in_executor(None, _query)

    async def set_metadata(self, key: str, value: str) -> bool:
        """Menyimpan atau memperbarui nilai metadata sistem."""
        loop = asyncio.get_running_loop()

        def _query():
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO system_metadata (key, value, updated_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(key) DO UPDATE SET
                            value = excluded.value,
                            updated_at = CURRENT_TIMESTAMP
                        """,
                        (key, str(value)),
                    )
                    conn.commit()
                return True
            except Exception as e:
                logger.error(f"set_metadata error for {key}: {e}")
                return False

        return await loop.run_in_executor(None, _query)

    async def get_chat_settings(self, chat_id: int) -> dict:
        """Mengambil konfigurasi preferensi grup."""
        loop = asyncio.get_running_loop()

        def _query():
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM chat_settings WHERE chat_id = ?", (chat_id,))
                    row = cursor.fetchone()
                    if row:
                        return dict(row)
                    # Inisialisasi default jika belum ada
                    cursor.execute(
                        "INSERT OR IGNORE INTO chat_settings (chat_id, auth_mode, default_volume, auto_leave_time) VALUES (?, 'everyone', 100, 300)",
                        (chat_id,),
                    )
                    conn.commit()
                    return {
                        "chat_id": chat_id,
                        "auth_mode": "everyone",
                        "default_volume": 100,
                        "auto_leave_time": 300,
                    }
            except Exception as e:
                logger.error(f"get_chat_settings error: {e}")
                return {
                    "chat_id": chat_id,
                    "auth_mode": "everyone",
                    "default_volume": 100,
                    "auto_leave_time": 300,
                }

        return await loop.run_in_executor(None, _query)

    async def update_chat_setting(self, chat_id: int, key: str, value: Any) -> bool:
        """Memperbarui satu preferensi konfigurasi grup."""
        if key not in ("auth_mode", "default_volume", "auto_leave_time", "autoplay"):
            return False
        loop = asyncio.get_running_loop()

        def _query():
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT OR IGNORE INTO chat_settings (chat_id) VALUES (?)",
                        (chat_id,),
                    )
                    cursor.execute(
                        f"UPDATE chat_settings SET {key} = ? WHERE chat_id = ?",
                        (value, chat_id),
                    )
                    conn.commit()
                return True
            except Exception as e:
                logger.error(f"update_chat_setting error: {e}")
                return False

        return await loop.run_in_executor(None, _query)

    async def get_autoplay(self, chat_id: int) -> bool:
        """Mengambil status Auto-Play di grup."""
        settings = await self.get_chat_settings(chat_id)
        return bool(settings.get("autoplay", 0))

    async def set_autoplay(self, chat_id: int, enabled: bool) -> bool:
        """Mengatur status Auto-Play di grup."""
        return await self.update_chat_setting(chat_id, "autoplay", 1 if enabled else 0)

    # ------------------------------------------------------------------ #
    #  Playlist Management Methods                                       #
    # ------------------------------------------------------------------ #

    async def add_to_playlist(self, user_id: int, track: dict) -> tuple[bool, str]:
        """Menambahkan satu lagu ke daftar playlist pengguna (Maks 50 lagu)."""
        loop = asyncio.get_running_loop()

        def _query():
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    # 1. Cek jumlah lagu di playlist
                    cursor.execute("SELECT COUNT(*) FROM playlists WHERE user_id = ?", (user_id,))
                    count = cursor.fetchone()[0]
                    if count >= 50:
                        return False, "Playlist Anda sudah penuh (Maksimal 50 lagu)."

                    # 2. Cek apakah lagu sudah ada di playlist
                    cursor.execute(
                        "SELECT id FROM playlists WHERE user_id = ? AND url = ?",
                        (user_id, track.get("url", "")),
                    )
                    if cursor.fetchone():
                        return False, "Lagu ini sudah ada di dalam playlist Anda."

                    # 3. Simpan ke database
                    cursor.execute(
                        """
                        INSERT INTO playlists (user_id, track_id, title, url, duration, channel, thumbnail)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            user_id,
                            track.get("id", ""),
                            track.get("title", "Tidak Diketahui"),
                            track.get("url", ""),
                            int(track.get("duration", 0)),
                            track.get("channel", "YouTube"),
                            track.get("thumbnail", ""),
                        ),
                    )
                    conn.commit()
                return True, "Lagu berhasil ditambahkan ke playlist!"
            except Exception as e:
                logger.error(f"add_to_playlist error: {e}")
                return False, f"Terjadi kesalahan database: {e}"

        return await loop.run_in_executor(None, _query)

    async def get_playlist(self, user_id: int) -> list[dict]:
        """Mengambil seluruh daftar lagu di playlist pengguna."""
        loop = asyncio.get_running_loop()

        def _query():
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT * FROM playlists WHERE user_id = ? ORDER BY id ASC",
                        (user_id,),
                    )
                    rows = cursor.fetchall()
                    return [dict(r) for r in rows]
            except Exception as e:
                logger.error(f"get_playlist error: {e}")
                return []

        return await loop.run_in_executor(None, _query)

    async def remove_from_playlist(self, user_id: int, index: int) -> tuple[bool, str]:
        """Menghapus lagu dari playlist berdasarkan nomor urut (1-based index)."""
        loop = asyncio.get_running_loop()

        def _query():
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id, title FROM playlists WHERE user_id = ? ORDER BY id ASC",
                        (user_id,),
                    )
                    rows = cursor.fetchall()
                    if not rows or index < 1 or index > len(rows):
                        return False, f"Nomor urut #{index} tidak ditemukan di playlist Anda."

                    target_row = rows[index - 1]
                    target_id = target_row["id"]
                    target_title = target_row["title"]

                    cursor.execute("DELETE FROM playlists WHERE id = ?", (target_id,))
                    conn.commit()
                return True, target_title
            except Exception as e:
                logger.error(f"remove_from_playlist error: {e}")
                return False, str(e)

        return await loop.run_in_executor(None, _query)

    async def clear_playlist(self, user_id: int) -> int:
        """Menghapus seluruh lagu di playlist pengguna."""
        loop = asyncio.get_running_loop()

        def _query():
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM playlists WHERE user_id = ?", (user_id,))
                    deleted = cursor.rowcount
                    conn.commit()
                    return deleted
            except Exception as e:
                logger.error(f"clear_playlist error: {e}")
                return 0

        return await loop.run_in_executor(None, _query)

    # ------------------------------------------------------------------ #
    #  Backup & Restore Methods                                          #
    # ------------------------------------------------------------------ #

    async def get_db_summary(self) -> dict:
        """Mengambil ringkasan data statistik database."""
        loop = asyncio.get_running_loop()

        def _query():
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM served_users")
                    users_cnt = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM served_chats")
                    chats_cnt = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM sudo_users")
                    sudos_cnt = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM playlists")
                    pl_cnt = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM gban_users")
                    gban_cnt = cursor.fetchone()[0]

                    file_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

                    return {
                        "users": users_cnt,
                        "chats": chats_cnt,
                        "sudos": sudos_cnt,
                        "playlists": pl_cnt,
                        "gbans": gban_cnt,
                        "size_bytes": file_size,
                        "db_path": self.db_path,
                    }
            except Exception as e:
                logger.error(f"get_db_summary error: {e}")
                return {
                    "users": 0,
                    "chats": 0,
                    "sudos": 0,
                    "playlists": 0,
                    "gbans": 0,
                    "size_bytes": 0,
                    "db_path": self.db_path,
                }

        return await loop.run_in_executor(None, _query)

    async def validate_and_restore_db(self, backup_file_path: str) -> tuple[bool, str | dict]:
        """Memvalidasi integritas file cadangan SQLite dan memulihkannya."""
        import shutil
        loop = asyncio.get_running_loop()

        def _restore():
            try:
                # 1. Validasi integritas file SQLite
                conn_test = sqlite3.connect(backup_file_path)
                cursor_test = conn_test.cursor()
                cursor_test.execute("PRAGMA integrity_check;")
                check = cursor_test.fetchone()
                if not check or check[0] != "ok":
                    conn_test.close()
                    return False, "File database rusak atau gagal uji integritas SQLite."

                # 2. Periksa keberadaan tabel inti
                cursor_test.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('served_users', 'served_chats')"
                )
                tables = [r[0] for r in cursor_test.fetchall()]
                conn_test.close()

                if "served_users" not in tables or "served_chats" not in tables:
                    return False, "File database tidak valid: Tabel utama tidak ditemukan."

                # 3. Buat file backup dari database saat ini sebagai pengaman
                if os.path.exists(self.db_path):
                    shutil.copy2(self.db_path, f"{self.db_path}.old")

                # 4. Gantikan file database aktif
                shutil.copy2(backup_file_path, self.db_path)

                # 5. Inisialisasi skema jika ada tabel baru
                self._init_db()
                self._load_gban_cache()

                # 6. Ambil ringkasan database baru
                with self._get_connection() as conn:
                    c = conn.cursor()
                    c.execute("SELECT COUNT(*) FROM served_users")
                    users_cnt = c.fetchone()[0]
                    c.execute("SELECT COUNT(*) FROM served_chats")
                    chats_cnt = c.fetchone()[0]
                    c.execute("SELECT COUNT(*) FROM sudo_users")
                    sudos_cnt = c.fetchone()[0]
                    c.execute("SELECT COUNT(*) FROM playlists")
                    pl_cnt = c.fetchone()[0]
                    c.execute("SELECT COUNT(*) FROM gban_users")
                    gban_cnt = c.fetchone()[0]

                return True, {
                    "users": users_cnt,
                    "chats": chats_cnt,
                    "sudos": sudos_cnt,
                    "playlists": pl_cnt,
                    "gbans": gban_cnt,
                }
            except Exception as e:
                logger.error(f"validate_and_restore_db error: {e}")
                return False, f"Terjadi kesalahan saat pemulihan: {e}"

        return await loop.run_in_executor(None, _restore)


db = Database()
