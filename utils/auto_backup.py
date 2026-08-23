# ==============================================================================
#  🇮🇩 Nusantara Stream - Telegram Music & Video Streaming Bot
# ==============================================================================
#  Author   : Amang (@BukanDevelopers)
#  GitHub   : https://github.com/amanqs
#  Project  : Nusantara Stream Telegram Bot
#  License  : GNU General Public License v3.0
# ==============================================================================

import asyncio
import datetime
import logging
import os
import shutil
from typing import Optional

try:
    from kurigram import Client
except ImportError:
    from pyrogram import Client

from config import Config
from utils.database import db
from utils.formatters import human_readable_size, clean_markdown

logger = logging.getLogger("NusantaraStream.AutoBackup")

# Runtime state
_AUTO_BACKUP_ENABLED = Config.AUTO_BACKUP_ENABLED if hasattr(Config, "AUTO_BACKUP_ENABLED") else True
_AUTO_BACKUP_INTERVAL_HOURS = Config.AUTO_BACKUP_INTERVAL_HOURS if hasattr(Config, "AUTO_BACKUP_INTERVAL_HOURS") else 24
_LAST_BACKUP_TIME: Optional[float] = None
_IS_BACKING_UP = False


def is_autobackup_enabled() -> bool:
    """Cek status apakah auto-backup aktif."""
    return _AUTO_BACKUP_ENABLED


def set_autobackup_enabled(enabled: bool) -> None:
    """Mengaktifkan / menonaktifkan auto-backup."""
    global _AUTO_BACKUP_ENABLED
    _AUTO_BACKUP_ENABLED = enabled


def get_autobackup_interval() -> int:
    """Mengambil interval auto-backup dalam satuan jam."""
    return _AUTO_BACKUP_INTERVAL_HOURS


def set_autobackup_interval(hours: int) -> int:
    """Mengatur interval auto-backup (minimal 1 jam, maksimal 168 jam/1 minggu)."""
    global _AUTO_BACKUP_INTERVAL_HOURS
    hours = max(1, min(168, hours))
    _AUTO_BACKUP_INTERVAL_HOURS = hours
    return hours


def get_last_backup_time() -> Optional[float]:
    """Mengambil timestamp eksekusi backup terakhir."""
    return _LAST_BACKUP_TIME


def format_autobackup_card(
    summary: dict,
    interval_hours: int,
    is_auto: bool = True,
) -> str:
    """Format tampilan kartu laporan auto backup database."""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    u_cnt = summary.get("users", 0)
    c_cnt = summary.get("chats", 0)
    s_cnt = summary.get("sudos", 0)
    p_cnt = summary.get("playlists", 0)
    size_str = human_readable_size(summary.get("size_bytes", 0))

    header = "⏰ Laporan Auto-Backup Otomatis" if is_auto else "💾 Laporan Pencadangan Database"
    sub = f"Waktu Eksekusi: `{now_str}`"

    return (
        f"| {header} |\n"
        "|:---:|\n"
        f"| {sub} |\n\n"
        "| Metrik Database | Statistik Sistem |\n"
        "|:---|:---|\n"
        f"| 👥 Pengguna Terlayani | `{u_cnt:,}` pengguna |\n"
        f"| 📢 Grup Terlayani | `{c_cnt:,}` grup |\n"
        f"| 🛡️ Sudo Administrator | `{s_cnt}` admin |\n"
        f"| 📂 Lagu Playlist Tersimpan | `{p_cnt:,}` lagu |\n"
        f"| 💾 Ukuran Berkas DB | `{size_str}` |\n"
        f"| ⏱ Interval Terjadwal | Setiap `{interval_hours}` Jam |\n\n"
        "| 💡 Berkas terlampir ini dapat dipulihkan kapan saja dengan membalas `/restore` |\n"
        "|:---:|\n"
        "| |"
    )


async def execute_and_send_backup(
    client: Client,
    target_chat_ids: list[int],
    is_auto: bool = True,
) -> bool:
    """Membuat salinan database dan mengirimkannya ke daftar chat tujuan."""
    global _LAST_BACKUP_TIME, _IS_BACKING_UP
    if _IS_BACKING_UP:
        logger.warning("Proses backup sedang berjalan. Melewati duplikasi trigger.")
        return False

    _IS_BACKING_UP = True
    temp_backup_path = ""
    try:
        db_path = getattr(db, "db_path", "nusantara_data.db")
        if not os.path.exists(db_path):
            logger.error(f"Berkas database {db_path} tidak ditemukan!")
            return False

        summary = await db.get_db_summary()
        file_date = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"nusantara_autobackup_{file_date}.db" if is_auto else f"nusantara_backup_{file_date}.db"
        temp_backup_path = os.path.join(Config.TEMP_DIR, backup_filename)

        # Salin database secara aman
        shutil.copy2(db_path, temp_backup_path)

        caption = format_autobackup_card(
            summary=summary,
            interval_hours=_AUTO_BACKUP_INTERVAL_HOURS,
            is_auto=is_auto,
        )

        sent_count = 0
        for chat_id in set(target_chat_ids):
            if not chat_id:
                continue
            try:
                await client.send_document(
                    chat_id=chat_id,
                    document=temp_backup_path,
                    file_name=backup_filename,
                    caption=caption,
                )
                sent_count += 1
                logger.info(f"Auto-backup berhasil dikirim ke {chat_id}")
            except Exception as e:
                logger.error(f"Gagal mengirim auto-backup ke chat {chat_id}: {e}")

        now_ts = datetime.datetime.now().timestamp()
        _LAST_BACKUP_TIME = now_ts
        await db.set_metadata("last_autobackup_time", str(now_ts))
        return sent_count > 0
    except Exception as e:
        logger.error(f"Error selama proses auto backup: {e}")
        return False
    finally:
        _IS_BACKING_UP = False
        if temp_backup_path and os.path.exists(temp_backup_path):
            try:
                os.remove(temp_backup_path)
            except Exception:
                pass


async def auto_backup_worker(client: Client):
    """Background worker loop yang mengeksekusi auto-backup secara berkala."""
    logger.info(
        f"Auto-Backup Worker diaktifkan (Interval: {_AUTO_BACKUP_INTERVAL_HOURS} Jam)."
    )

    while True:
        try:
            # Periksa timestamp backup terakhir dari database
            now_ts = datetime.datetime.now().timestamp()
            last_ts_str = await db.get_metadata("last_autobackup_time", "0")
            try:
                last_ts = float(last_ts_str)
            except (ValueError, TypeError):
                last_ts = 0.0

            interval_seconds = _AUTO_BACKUP_INTERVAL_HOURS * 3600
            elapsed = now_ts - last_ts

            if elapsed < interval_seconds and last_ts > 0:
                remaining_seconds = interval_seconds - elapsed
                hours_left = remaining_seconds / 3600
                logger.info(
                    f"Auto-Backup terakhir baru saja dikirim ({int(elapsed / 60)} menit lalu). "
                    f"Jadwal backup berikutnya dalam {hours_left:.1f} jam."
                )
                await asyncio.sleep(remaining_seconds)
                continue

            if _AUTO_BACKUP_ENABLED:
                target_chats = []
                if Config.LOG_GROUP_ID:
                    target_chats.append(Config.LOG_GROUP_ID)
                if Config.OWNER_ID:
                    target_chats.append(Config.OWNER_ID)

                if target_chats:
                    logger.info("Menjalankan jadwal pencadangan otomatis (Auto-Backup)...")
                    await execute_and_send_backup(client, target_chats, is_auto=True)
                else:
                    logger.warning("Auto-backup aktif tetapi LOG_GROUP_ID & OWNER_ID belum diatur.")

            # Tidur selama interval jam yang dikonfigurasi
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            logger.info("Auto-Backup Worker dihentikan.")
            break
        except Exception as e:
            logger.error(f"Error pada auto_backup_worker: {e}")
            await asyncio.sleep(300)  # Coba lagi 5 menit jika terjadi error sistem
