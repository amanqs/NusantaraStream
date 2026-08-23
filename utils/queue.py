# ==============================================================================
#  🇮🇩 Nusantara Stream - Telegram Music & Video Streaming Bot
# ==============================================================================
#  Author   : Amang (@BukanDevelopers)
#  GitHub   : https://github.com/amanqs
#  Project  : Nusantara Stream Telegram Bot
#  License  : GNU General Public License v3.0
# ==============================================================================

import random
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TrackInfo:
    """Struktur data representasi sebuah lagu atau video."""

    title: str
    url: str
    stream_url: str
    duration: int  # dalam detik
    channel: str = "YouTube"
    thumbnail: Optional[str] = None
    requested_by_id: int = 0
    requested_by_name: str = "Pengguna"
    is_video: bool = False
    is_live: bool = False
    video_url: Optional[str] = None
    file_path: Optional[str] = None
    file_id: Optional[str] = None
    is_autoplay: bool = False
    start_time: float = field(default_factory=time.time)

    @property
    def elapsed_seconds(self) -> int:
        """Menghitung durasi pemutaran yang telah berjalan."""
        return int(time.time() - self.start_time)


class QueueManager:
    """Manajer Antrean & Status Pemutaran Per-Grup."""

    def __init__(self):
        # chat_id -> list[TrackInfo]
        self._queues: dict[int, list[TrackInfo]] = {}
        # chat_id -> TrackInfo
        self._current_tracks: dict[int, Optional[TrackInfo]] = {}
        # chat_id -> TrackInfo (lagu terakhir yang diputar)
        self._last_played_tracks: dict[int, Optional[TrackInfo]] = {}
        # chat_id -> list[str] (riwayat lagu yang sudah diputar)
        self._played_history: dict[int, list[str]] = {}
        # chat_id -> bool (Auto-Play rekomendasi saat antrean habis)
        self._autoplay_modes: dict[int, bool] = {}
        # chat_id -> bool (Looping track saat ini)
        self._loop_modes: dict[int, bool] = {}
        # chat_id -> int (Tingkat volume 0-200)
        self._volumes: dict[int, int] = {}
        # chat_id -> bool (Status jeda)
        self._paused: dict[int, bool] = {}
        # chat_id -> bool (Status mute)
        self._muted: dict[int, bool] = {}
        # chat_id -> int (Message ID kartu Now Playing)
        self._now_playing_msgs: dict[int, Optional[int]] = {}
        # chat_id -> float (Timestamp update terakhir untuk rate limiter)
        self._last_ui_update: dict[int, float] = {}

    def get_queue(self, chat_id: int) -> list[TrackInfo]:
        """Mengambil daftar antrean di grup tertentu."""
        return self._queues.get(chat_id, [])

    def get_current_track(self, chat_id: int) -> Optional[TrackInfo]:
        """Mengambil lagu yang sedang diputar di grup tertentu."""
        return self._current_tracks.get(chat_id, None)

    def set_current_track(self, chat_id: int, track: Optional[TrackInfo]) -> None:
        """Mengatur lagu yang sedang diputar."""
        if track:
            track.start_time = time.time()
            self._last_played_tracks[chat_id] = track
            # Catat riwayat
            if chat_id not in self._played_history:
                self._played_history[chat_id] = []
            if track.url:
                self._played_history[chat_id].append(track.url)
            if track.title:
                self._played_history[chat_id].append(track.title)
            # Batasi riwayat maksimal 50 lagu
            if len(self._played_history[chat_id]) > 50:
                self._played_history[chat_id] = self._played_history[chat_id][-50:]

        self._current_tracks[chat_id] = track
        self._paused[chat_id] = False

    def add_to_queue(self, chat_id: int, track: TrackInfo) -> int:
        """Menambahkan lagu ke antrean dan mengembalikan posisi antrean."""
        if chat_id not in self._queues:
            self._queues[chat_id] = []
        self._queues[chat_id].append(track)
        return len(self._queues[chat_id])

    def get_next_track(self, chat_id: int) -> Optional[TrackInfo]:
        """Mengambil lagu berikutnya dengan memperhatikan mode loop."""
        current = self.get_current_track(chat_id)

        # Jika mode loop aktif, putar kembali lagu yang sama
        if current and self.is_loop_enabled(chat_id):
            current.start_time = time.time()
            return current

        # Ambil dari antrean
        queue = self._queues.get(chat_id, [])
        if queue:
            next_track = queue.pop(0)
            self.set_current_track(chat_id, next_track)
            return next_track

        # Antrean kosong
        self.set_current_track(chat_id, None)
        return None

    def skip_track(self, chat_id: int) -> Optional[TrackInfo]:
        """Melompati lagu saat ini dan mengambil lagu berikutnya."""
        queue = self._queues.get(chat_id, [])
        if queue:
            next_track = queue.pop(0)
            self.set_current_track(chat_id, next_track)
            return next_track

        self.set_current_track(chat_id, None)
        return None

    def shuffle_queue(self, chat_id: int) -> bool:
        """Mengacak urutan lagu di dalam antrean."""
        queue = self._queues.get(chat_id, [])
        if len(queue) > 1:
            random.shuffle(queue)
            return True
        return False

    def toggle_loop(self, chat_id: int) -> bool:
        """Mengaktifkan / menonaktifkan mode loop lagu."""
        current_state = self._loop_modes.get(chat_id, False)
        new_state = not current_state
        self._loop_modes[chat_id] = new_state
        return new_state

    def is_loop_enabled(self, chat_id: int) -> bool:
        """Cek apakah mode loop aktif di grup."""
        return self._loop_modes.get(chat_id, False)

    def set_volume(self, chat_id: int, volume: int) -> int:
        """Mengatur volume per grup (dibatasi 1-200%)."""
        volume = max(1, min(200, volume))
        self._volumes[chat_id] = volume
        return volume

    def get_volume(self, chat_id: int) -> int:
        """Mengambil level volume saat ini di grup."""
        return self._volumes.get(chat_id, 100)

    def set_paused(self, chat_id: int, is_paused: bool) -> None:
        """Mengatur status jeda pemutaran."""
        self._paused[chat_id] = is_paused

    def is_paused(self, chat_id: int) -> bool:
        """Cek apakah pemutaran sedang dijeda."""
        return self._paused.get(chat_id, False)

    def set_muted(self, chat_id: int, is_muted: bool) -> None:
        """Mengatur status bisu (mute) pemutaran."""
        self._muted[chat_id] = is_muted

    def is_muted(self, chat_id: int) -> bool:
        """Cek apakah pemutaran sedang dibisukan (muted)."""
        return self._muted.get(chat_id, False)

    def toggle_mute(self, chat_id: int) -> bool:
        """Mengubah status mute pemutaran."""
        current = self.is_muted(chat_id)
        new_state = not current
        self._muted[chat_id] = new_state
        return new_state

    def set_now_playing_msg(self, chat_id: int, message_id: Optional[int]) -> None:
        """Menyimpan ID pesan Now Playing untuk keperluan auto update / delete."""
        self._now_playing_msgs[chat_id] = message_id

    def get_now_playing_msg(self, chat_id: int) -> Optional[int]:
        """Mengambil ID pesan Now Playing."""
        return self._now_playing_msgs.get(chat_id, None)

    def can_update_ui(self, chat_id: int, interval: float = 7.0) -> bool:
        """Rate limiter untuk mencegah FloodWait Telegram saat mengedit pesan."""
        now = time.time()
        last = self._last_ui_update.get(chat_id, 0.0)
        if now - last >= interval:
            self._last_ui_update[chat_id] = now
            return True
        return False

    def set_autoplay(self, chat_id: int, enabled: bool) -> None:
        """Mengatur status Auto-Play di grup."""
        self._autoplay_modes[chat_id] = enabled

    def is_autoplay_enabled(self, chat_id: int) -> bool:
        """Cek apakah mode Auto-Play aktif di grup."""
        return self._autoplay_modes.get(chat_id, False)

    def toggle_autoplay(self, chat_id: int) -> bool:
        """Toggle status mode Auto-Play di grup."""
        current = self.is_autoplay_enabled(chat_id)
        new_state = not current
        self._autoplay_modes[chat_id] = new_state
        return new_state

    def get_last_played_track(self, chat_id: int) -> Optional[TrackInfo]:
        """Mengambil info lagu terakhir yang pernah diputar di grup."""
        return self._last_played_tracks.get(chat_id, None)

    def get_played_history(self, chat_id: int) -> list[str]:
        """Mengambil daftar riwayat lagu yang telah diputar di grup."""
        return self._played_history.get(chat_id, [])

    def clear_queue(self, chat_id: int) -> None:
        """Menghapus seluruh antrean dan data pemutaran di grup."""
        self._queues.pop(chat_id, None)
        self._current_tracks.pop(chat_id, None)
        self._loop_modes.pop(chat_id, None)
        self._paused.pop(chat_id, None)
        self._now_playing_msgs.pop(chat_id, None)
        self._last_ui_update.pop(chat_id, None)

    def get_active_chats(self) -> list[int]:
        """Mengambil daftar semua grup yang sedang aktif memutar lagu."""
        return [cid for cid, track in self._current_tracks.items() if track is not None]


# Instance global singleton untuk manajemen antrean
queue_manager = QueueManager()
