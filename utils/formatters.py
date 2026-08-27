# ==============================================================================
#  🇮🇩 Nusantara Stream - Telegram Music & Video Streaming Bot
# ==============================================================================
#  Author   : Amang (@BukanDevelopers)
#  GitHub   : https://github.com/amanqs
#  Project  : Nusantara Stream Telegram Bot
#  License  : GNU General Public License v3.0
# ==============================================================================

import re
from config import Config


def clean_markdown(text: str) -> str:
    """Membersihkan karakter khusus Markdown agar tidak merusak formatting."""
    if not text:
        return ""
    return str(text).replace("[", "(").replace("]", ")")


def get_readable_time(seconds: int | float | None) -> str:
    """Mengubah detik menjadi format waktu yang mudah dibaca (MM:SS atau HH:MM:SS)."""
    if seconds is None or seconds < 0:
        return "00:00"

    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def human_readable_size(size_in_bytes: int | float | None) -> str:
    """Mengubah ukuran bytes menjadi format yang mudah dibaca (KB, MB, GB)."""
    if not size_in_bytes or size_in_bytes < 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_in_bytes)
    unit_idx = 0
    while size >= 1024 and unit_idx < len(units) - 1:
        size /= 1024
        unit_idx += 1
    return f"{size:.2f} {units[unit_idx]}"


def format_download_progress_card(
    file_name: str,
    current_bytes: int,
    total_bytes: int,
    speed: float = 0,
    eta: int = 0,
) -> str:
    """Format tampilan progres download media Telegram dalam bentuk Telegram Table Card."""
    clean_name = clean_markdown(file_name or "Telegram_Media").replace("|", "\\|")
    if len(clean_name) > 30:
        clean_name = clean_name[:27] + "..."

    percent = (current_bytes / total_bytes * 100) if total_bytes > 0 else 0
    percent_str = f"{percent:.1f}%"

    bar_len = 10
    filled = int(percent / 100 * bar_len)
    bar = "▰" * filled + "▱" * (bar_len - filled)
    if len(bar) > bar_len:
        bar = bar[:bar_len]

    cur_size = human_readable_size(current_bytes)
    tot_size = human_readable_size(total_bytes)
    speed_str = f"{human_readable_size(speed)}/s" if speed > 0 else "Menghitung..."
    eta_str = get_readable_time(eta) if eta > 0 else "00:00"

    card = (
        "| 📥 Mengunduh File Media Telegram |\n"
        "|:---:|\n"
        f"| File: `{clean_name}` |\n\n"
        "| Parameter | Status Unduhan |\n"
        "|:---|:---|\n"
        f"| 📊 Progress | `[{bar}] {percent_str}` |\n"
        f"| 💾 Ukuran | `{cur_size} / {tot_size}` |\n"
        f"| ⚡ Kecepatan | `{speed_str}` |\n"
        f"| ⏱️ Estimasi (ETA) | `{eta_str}` |\n\n"
        "| 🤖 Nusantara Stream Engine 🤖 |\n"
        "|:---:|\n"
        "| |"
    )
    return card


def format_broadcast_progress_card(
    target_type: str,
    current: int,
    total: int,
    success: int,
    failed: int,
    speed: float = 0,
    eta: int = 0,
) -> str:
    """Format tampilan live progres pengiriman broadcast dalam bentuk Telegram Table Card."""
    percent = (current / total * 100) if total > 0 else 0
    percent_str = f"{percent:.1f}%"

    bar_len = 10
    filled = int(percent / 100 * bar_len)
    bar = "▰" * filled + "▱" * (bar_len - filled)
    if len(bar) > bar_len:
        bar = bar[:bar_len]

    speed_str = f"{speed:.1f} msg/s" if speed > 0 else "Menghitung..."
    eta_str = get_readable_time(eta) if eta > 0 else "00:00"

    card = (
        "| 📢 Pengiriman Broadcast Berjalan |\n"
        "|:---:|\n"
        f"| Target: `{target_type}` |\n\n"
        "| Parameter | Status Broadcast |\n"
        "|:---|:---|\n"
        f"| 📊 Progress | `[{bar}] {percent_str}` |\n"
        f"| 🎯 Terproses | `{current} / {total}` |\n"
        f"| ✅ Berhasil | `{success}` |\n"
        f"| ❌ Gagal / Blokir | `{failed}` |\n"
        f"| ⚡ Kecepatan | `{speed_str}` |\n"
        f"| ⏱️ Sisa Waktu (ETA) | `{eta_str}` |\n\n"
        "| 🤖 Nusantara Stream Engine 🤖 |\n"
        "|:---:|\n"
        "| |"
    )
    return card


def format_broadcast_finished_card(
    target_type: str,
    total: int,
    success: int,
    failed: int,
    elapsed_sec: int | float,
) -> str:
    """Format laporan akhir hasil pengiriman broadcast dalam bentuk Telegram Table Card."""
    elapsed_str = get_readable_time(elapsed_sec)
    success_rate = (success / total * 100) if total > 0 else 100.0

    card = (
        "| 📢 Laporan Broadcast Selesai |\n"
        "|:---:|\n"
        f"| Target Distribusi: `{target_type}` |\n\n"
        "| Parameter | Hasil Laporan |\n"
        "|:---|:---|\n"
        f"| 🎯 Total Penerima | `{total}` |\n"
        f"| ✅ Berhasil Terkirim | `{success}` ({success_rate:.1f}%) |\n"
        f"| ❌ Gagal Terkirim | `{failed}` |\n"
        f"| ⏱️ Total Waktu | `{elapsed_str}` |\n\n"
        "| 🤖 Nusantara Stream Engine 🤖 |\n"
        "|:---:|\n"
        "| |"
    )
    return card


def generate_progress_bar(
    current_sec: int,
    total_sec: int,
    bar_length: int = 12,
    fill_char: str = "━",
    empty_char: str = "─",
    slider_char: str = "🔘",
) -> str:
    """Membuat visual progress bar modern dengan Markdown Native."""
    if total_sec <= 0:
        return f"`[{slider_char}{fill_char * (bar_length - 1)}]`\n`(🔴 Live)`"

    current_sec = min(max(0, current_sec), total_sec)
    progress_ratio = current_sec / total_sec
    slider_pos = int(progress_ratio * (bar_length - 1))

    bar = (
        fill_char * slider_pos
        + slider_char
        + empty_char * (bar_length - 1 - slider_pos)
    )
    current_time_str = get_readable_time(current_sec)
    total_time_str = get_readable_time(total_sec)

    return f"`[{bar}]`\n`{current_time_str} / {total_time_str}`"


def get_clean_youtube_thumbnail(url_or_query: str, thumb_url: str = None) -> str:
    """Mendapatkan URL thumbnail YouTube JPEG bersih untuk Telegram Rich Message."""
    target_str = f"{url_or_query or ''} {thumb_url or ''}"
    yt_match = re.search(r"(?:v=|\/|vi\/|vi_webp\/|embed\/|shorts\/)([0-9A-Za-z_-]{11})", target_str)
    if yt_match:
        video_id = yt_match.group(1)
        return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

    if thumb_url and str(thumb_url).startswith("http") and not thumb_url.endswith(".webp"):
        return thumb_url.split("?")[0]
    return ""


def format_now_playing(
    track,
    current_sec: int = 0,
    is_paused: bool = False,
    is_looping: bool = False,
    volume: int = 100,
    is_muted: bool = False,
) -> str:
    """Format tampilan Now Playing bergaya Telegram Rich Message Table Card."""
    clean_title = clean_markdown(track.title).replace("|", "\\|")
    clean_requester = clean_markdown(track.requested_by_name or "Pengguna").replace("|", "\\|")

    stream_format = "🔘 Video" if track.is_video else "🔘 Audio"
    duration_display = "🔴 Live" if track.is_live else get_readable_time(track.duration)

    status_header = "⏸ Media Dijeda" if is_paused else "🔴 Media Sedang Diputar"
    if is_muted:
        status_header = "🔇 Media Dibisukan (Muted)"

    is_tv = track.is_live and ("iptv" in str(track.channel).lower() or ".m3u8" in str(track.url).lower())
    if is_tv:
        title_display = f"`{clean_title}`"
        media_label = "📺 Saluran TV"
        media_part = ""
    elif track.url and track.url.startswith("http") and not track.url.endswith(".m3u8"):
        title_display = f"[{clean_title}]({track.url})"
        media_label = "▶️ Judul Media"
        clean_thumb = get_clean_youtube_thumbnail(track.url, getattr(track, "thumbnail", None))
        media_part = f"![]({clean_thumb})\n\n" if clean_thumb else ""
    else:
        title_display = f"`{clean_title}`"
        media_label = "▶️ Judul Media"
        media_part = ""

    text = (
        f"{media_part}"
        f"| {status_header} |\n"
        f"|:---:|\n"
        f"| |\n\n"
        f"| Parameter | Detail Informasi |\n"
        f"|:---|:---|\n"
        f"| {media_label} | {title_display} |\n"
        f"| 🎬 Format Stream | {stream_format} |\n"
        f"| 👤 Diminta oleh | {clean_requester} |\n"
        f"| ⏱ Total Durasi | {duration_display} |\n\n"
        f"| 🤖 Nusantara Stream 🤖 |\n"
        f"|:---:|\n"
        f"| |"
    )
    return text


def format_queue_list(
    queue_list: list,
    current_track,
    current_page: int = 1,
    page_size: int = 5,
) -> str:
    """Format daftar antrean musik dengan Telegram Native Rich Table Card."""
    total_tracks = len(queue_list)
    total_pages = max(1, (total_tracks + page_size - 1) // page_size)
    current_page = min(max(1, current_page), total_pages)

    text = (
        "| 📋 Daftar Antrean Musik |\n"
        "|:---:|\n"
        "| |\n\n"
    )

    if current_track:
        c_title = clean_markdown(current_track.title).replace("|", "\\|")
        c_dur = (
            "🔴 Live"
            if current_track.is_live
            else get_readable_time(current_track.duration)
        )
        c_req = clean_markdown(current_track.requested_by_name or "Pengguna").replace("|", "\\|")
        c_type = "🎬 Video" if current_track.is_video else "🔘 Audio"
        text += (
            f"| Sedang Diputar | Detail Informasi |\n"
            f"|:---|:---|\n"
            f"| ▶️ Judul Media | [{c_title}]({current_track.url}) |\n"
            f"| ⏱ Durasi | {c_dur} |\n"
            f"| 👤 Diminta oleh | {c_req} |\n"
            f"| 🎬 Format | {c_type} |\n\n\n"
        )

    if not queue_list:
        text += (
            "| 📭 Antrean Berikutnya Kosong |\n"
            "|:---:|\n"
            "| Belum ada lagu lain di daftar antrean |\n\n"
        )
    else:
        start_idx = (current_page - 1) * page_size
        end_idx = min(start_idx + page_size, total_tracks)

        text += (
            "| No | Lagu Berikutnya | Durasi |\n"
            "|:---:|:---|:---:|\n"
        )
        for idx, track in enumerate(queue_list[start_idx:end_idx], start=start_idx + 1):
            t_title = clean_markdown(track.title[:30]).replace("|", "\\|")
            t_dur = (
                "🔴 Live" if track.is_live else get_readable_time(track.duration)
            )
            t_icon = "🎬" if track.is_video else "🎵"
            text += f"| #{idx} | {t_icon} [{t_title}]({track.url}) | {t_dur} |\n"
        text += "\n"

    text += (
        f"| 📄 Halaman: {current_page}/{total_pages} • Total: {total_tracks} Lagu |\n"
        f"|:---:|\n"
        f"| |"
    )
    return text


def format_single_search_result(
    item: dict,
    current_idx: int,
    total_results: int,
) -> str:
    """Format 1 hasil pencarian YouTube interaktif dengan Telegram Rich Table Card."""
    raw_title = item.get("title", "Tidak Diketahui")
    title = clean_markdown(raw_title).replace("|", "\\|")
    duration = item.get("duration_string") or get_readable_time(
        item.get("duration", 0)
    )
    channel = clean_markdown(item.get("channel", "YouTube")).replace("|", "\\|")
    url = item.get("url", "https://youtube.com")
    position_str = f"Hasil ke-{current_idx + 1} dari {total_results}"

    clean_thumb = get_clean_youtube_thumbnail(url, item.get("thumbnail"))
    media_part = f"![]({clean_thumb})\n\n" if clean_thumb else ""

    text = (
        f"{media_part}"
        "| 🔍 Hasil Pencarian YouTube |\n"
        "|:---:|\n"
        "| |\n\n"
        "| Parameter | Detail Informasi |\n"
        "|:---|:---|\n"
        f"| 💿 Judul Media | [{title}]({url}) |\n"
        f"| ⏱ Durasi | {duration} |\n"
        f"| 📡 Channel | {channel} |\n"
        f"| 📄 Posisi | {position_str} |\n\n"
        "| 💡 Geser menggunakan tombol panah jika tidak sesuai, lalu pilih format: |\n"
        "|:---:|\n"
        "| |"
    )
    return text


def format_search_results(query: str, results: list) -> str:
    """Format daftar hasil pencarian YouTube."""
    if results:
        return format_single_search_result(results[0], 0, len(results))
    clean_query = clean_markdown(query).replace("|", "\\|")
    return (
        "| 🔍 Hasil Pencarian YouTube |\n"
        "|:---:|\n"
        f"| Kata Kunci: `{clean_query}` |\n\n"
        "| Tidak ada hasil ditemukan |\n"
        "|:---:|\n"
        "| |"
    )


try:
    from kurigram.types import InputRichMessage
except ImportError:
    try:
        from pyrogram.types import InputRichMessage
    except ImportError:
        class InputRichMessage:
            def __init__(self, markdown: str = "", html: str = "", **kwargs):
                self.markdown = markdown
                self.html = html


from utils.rich_parser import RichParser


def to_rich_message(markdown_text: str) -> InputRichMessage:
    """Mengubah format Markdown Rich Message menjadi objek InputRichMessage (Telegram Bot API 10.x)."""
    return RichParser.get_input_rich_message(markdown_text)
