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
from typing import Optional

try:
    from kurigram.types import LinkPreviewOptions
except ImportError:
    from pyrogram.types import LinkPreviewOptions

from config import Config
from core.bot import bot_client
from core.userbot import userbot_client
from utils.formatters import format_now_playing
from utils.keyboards import get_control_panel
from utils.queue import queue_manager, TrackInfo
from utils.rich_parser import RichParser

logger = logging.getLogger("NusantaraStream.Calls")

# Import PyTgCalls dengan penanganan multi-versi yang aman
try:
    from pytgcalls import PyTgCalls
    from pytgcalls.types import AudioQuality, VideoQuality, MediaStream
    from pytgcalls.mtproto.bridged_client import BridgedClient

    # Patch agar PyTgCalls mengenali Kurigram dan custom client subclass
    _orig_pkg_name = BridgedClient.package_name

    def _safe_pkg_name(obj):
        pkg = _orig_pkg_name(obj)
        if pkg in ("core", "kurigram", "userbot", "NusantaraStream"):
            return "pyrogram"
        return pkg

    BridgedClient.package_name = staticmethod(_safe_pkg_name)

    # Patch PyObject recursion bug in PyTgCalls v2
    try:
        from pytgcalls.types.py_object import PyObject
        PyObject.default = staticmethod(lambda obj: repr(obj))
        PyObject.__str__ = lambda self: f"<{self.__class__.__name__}>"
        PyObject.__repr__ = lambda self: f"<{self.__class__.__name__}>"
    except Exception:
        pass

    PYTGCALLS_AVAILABLE = True
except ImportError:
    try:
        from pytgcalls import PyTgCalls
        from pytgcalls.types.input_stream import AudioPiped, AudioVideoPiped
        PYTGCALLS_AVAILABLE = True
    except ImportError:
        PYTGCALLS_AVAILABLE = False
        logger.warning(
            "PyTgCalls belum terpasang. Voice Chat streaming akan dinonaktifkan."
        )


class CallManager:
    """Manajer Voice Chat PyTgCalls untuk Streaming Audio & Video."""

    def __init__(self):
        self.call: Optional[PyTgCalls] = None
        self._is_running = False

    def init_client(self):
        """Inisialisasi instance PyTgCalls dengan userbot client."""
        from core.security import enforce_integrity
        enforce_integrity()
        if not PYTGCALLS_AVAILABLE:
            return

        if not getattr(userbot_client, "is_connected", False):
            logger.warning("Userbot belum terhubung! PyTgCalls tidak dapat berjalan.")
            return

        self.call = PyTgCalls(userbot_client)
        self._register_handlers()

    def _register_handlers(self):
        """Mendaftarkan event listener ketika stream selesai."""
        if not self.call:
            return

        self._finished_locks = {}

        # Listener ketika lagu selesai diputar
        try:
            # Modern PyTgCalls Handler
            @self.call.on_update()
            async def on_stream_update(client, update):
                update_type = getattr(update, "__class__", {}).__name__
                if update_type == "StreamEnded":
                    chat_id = getattr(update, "chat_id", None)
                    if chat_id:
                        import time
                        now = time.time()
                        last_time = self._finished_locks.get(chat_id, 0)
                        if now - last_time > 3.0:
                            self._finished_locks[chat_id] = now
                            await self.on_track_finished(chat_id)
        except Exception as e:
            logger.debug(f"Pendaftaran on_update listener: {e}")

    async def start(self):
        """Menjalankan engine streaming PyTgCalls."""
        if self.call and not self._is_running:
            try:
                await self.call.start()
                self._is_running = True
                logger.info("PyTgCalls Engine berhasil dijalankan.")
            except Exception as e:
                logger.error(f"Gagal memulai PyTgCalls: {e}")

    async def stop(self):
        """Menghentikan engine PyTgCalls."""
        if self.call and self._is_running:
            try:
                # Tutup semua call yang aktif
                for chat_id in queue_manager.get_active_chats():
                    await self.leave_call(chat_id)
                self._is_running = False
                logger.info("PyTgCalls Engine dihentikan.")
            except Exception as e:
                logger.error(f"Gagal menghentikan PyTgCalls: {e}")

    def _create_stream(self, track: TrackInfo):
        """Membuat objek Stream kompatibel dengan versi PyTgCalls."""
        try:
            # Modern PyTgCalls 1.x / 2.x
            if track.is_video:
                v_path = track.video_url or track.file_path or track.stream_url
                return MediaStream(
                    media_path=v_path,
                    audio_parameters=AudioQuality.HIGH,
                    video_parameters=VideoQuality.HD_720p,
                )
            else:
                return MediaStream(
                    media_path=track.file_path or track.stream_url,
                    audio_parameters=AudioQuality.HIGH,
                    video_flags=MediaStream.Flags.IGNORE,
                )
        except Exception as e:
            logger.debug(f"MediaStream fallback: {e}")
            try:
                from pytgcalls.types.input_stream import AudioPiped, AudioVideoPiped
                if track.is_video:
                    return AudioVideoPiped(track.video_url or track.stream_url)
                return AudioPiped(track.file_path or track.stream_url)
            except Exception:
                raise e

    async def _ensure_client_ready(self):
        """Memastikan instance PyTgCalls siap dan terhubung secara dinamis."""
        if not self.call and PYTGCALLS_AVAILABLE:
            if getattr(userbot_client, "is_connected", False):
                self.init_client()
                if self.call and not self._is_running:
                    try:
                        await self.start()
                    except Exception as e:
                        logger.error(f"Gagal menjalankan PyTgCalls auto-start: {e}")

    async def play_stream(self, chat_id: int, track: TrackInfo) -> bool:
        """Memutar stream audio/video di grup."""
        await self._ensure_client_ready()
        if not self.call:
            raise RuntimeError("PyTgCalls belum diinisialisasi. Pastikan STRING_SESSION asisten aktif.")

        stream = self._create_stream(track)

        try:
            # Coba ganti stream jika sudah dalam voice chat
            if hasattr(self.call, "change_stream"):
                try:
                    await self.call.change_stream(chat_id, stream)
                except Exception:
                    # Jika belum join, lakukan join/play
                    if hasattr(self.call, "play"):
                        await self.call.play(chat_id, stream)
                    elif hasattr(self.call, "join_group_call"):
                        await self.call.join_group_call(chat_id, stream)
            elif hasattr(self.call, "play"):
                await self.call.play(chat_id, stream)
            elif hasattr(self.call, "join_group_call"):
                await self.call.join_group_call(chat_id, stream)

            queue_manager.set_current_track(chat_id, track)
            queue_manager.set_paused(chat_id, False)
            return True
        except Exception as e:
            logger.error(f"Error saat memutar stream di chat {chat_id}: {e}")
            raise e

    async def pause_stream(self, chat_id: int) -> bool:
        """Menjeda pemutaran musik."""
        if not self.call:
            return False

        try:
            if hasattr(self.call, "pause_stream"):
                await self.call.pause_stream(chat_id)
            elif hasattr(self.call, "pause"):
                await self.call.pause(chat_id)
            queue_manager.set_paused(chat_id, True)
            return True
        except Exception as e:
            logger.error(f"Error pause di chat {chat_id}: {e}")
            return False

    async def resume_stream(self, chat_id: int) -> bool:
        """Melanjutkan pemutaran musik yang dijeda."""
        if not self.call:
            return False

        try:
            if hasattr(self.call, "resume_stream"):
                await self.call.resume_stream(chat_id)
            elif hasattr(self.call, "resume"):
                await self.call.resume(chat_id)
            queue_manager.set_paused(chat_id, False)
            return True
        except Exception as e:
            logger.error(f"Error resume di chat {chat_id}: {e}")
            return False

    async def mute_stream(self, chat_id: int) -> bool:
        """Membisukan suara asisten di Voice Chat."""
        if not self.call:
            return False

        try:
            if hasattr(self.call, "mute_stream"):
                await self.call.mute_stream(chat_id)
            elif hasattr(self.call, "mute"):
                await self.call.mute(chat_id)
            queue_manager.set_muted(chat_id, True)
            return True
        except Exception as e:
            logger.error(f"Error mute di chat {chat_id}: {e}")
            return False

    async def unmute_stream(self, chat_id: int) -> bool:
        """Membuka suara asisten di Voice Chat."""
        if not self.call:
            return False

        try:
            if hasattr(self.call, "unmute_stream"):
                await self.call.unmute_stream(chat_id)
            elif hasattr(self.call, "unmute"):
                await self.call.unmute(chat_id)
            queue_manager.set_muted(chat_id, False)
            return True
        except Exception as e:
            logger.error(f"Error unmute di chat {chat_id}: {e}")
            return False

    async def change_volume(self, chat_id: int, volume: int) -> int:
        """Mengubah volume pemutaran (1-200%)."""
        if not self.call:
            return 100

        target_vol = queue_manager.set_volume(chat_id, volume)
        try:
            if hasattr(self.call, "change_volume_call"):
                await self.call.change_volume_call(chat_id, target_vol)
            elif hasattr(self.call, "set_volume"):
                await self.call.set_volume(chat_id, target_vol)
            return target_vol
        except Exception as e:
            logger.error(f"Error set volume di chat {chat_id}: {e}")
            return target_vol

    async def skip_stream(self, chat_id: int) -> Optional[TrackInfo]:
        """Melompati lagu saat ini dan memutar lagu berikutnya di antrean."""
        next_track = queue_manager.get_next_track(chat_id)
        if next_track:
            await self.play_stream(chat_id, next_track)
            return next_track
        elif queue_manager.is_autoplay_enabled(chat_id):
            try:
                last_track = queue_manager.get_last_played_track(chat_id)
                history = queue_manager.get_played_history(chat_id)
                from utils.ytdl import ytdl_helper
                rec_track = await ytdl_helper.get_recommended_track(last_track, history)
                if rec_track:
                    queue_manager.set_current_track(chat_id, rec_track)
                    await self.play_stream(chat_id, rec_track)
                    return rec_track
            except Exception as e:
                logger.error(f"Skip auto-play error di {chat_id}: {e}")
            await self.leave_call(chat_id)
            return None
        else:
            await self.leave_call(chat_id)
            return None

    async def leave_call(self, chat_id: int) -> bool:
        """Keluar dari voice chat grup dan membersihkan antrean."""
        if not self.call:
            return False

        try:
            if hasattr(self.call, "leave_call"):
                await self.call.leave_call(chat_id)
            elif hasattr(self.call, "leave_group_call"):
                await self.call.leave_group_call(chat_id)
        except Exception as e:
            logger.debug(f"Leave call di {chat_id}: {e}")

        queue_manager.clear_queue(chat_id)
        return True

    async def on_track_finished(self, chat_id: int):
        """Handler ketika sebuah lagu selesai diputar."""
        logger.info(f"Lagu di grup {chat_id} telah selesai.")
        next_track = queue_manager.get_next_track(chat_id)

        if next_track:
            try:
                await self.play_stream(chat_id, next_track)
                text = format_now_playing(
                    track=next_track,
                    current_sec=0,
                    is_paused=False,
                    is_looping=queue_manager.is_loop_enabled(chat_id),
                    volume=queue_manager.get_volume(chat_id),
                    is_muted=queue_manager.is_muted(chat_id),
                )
                markup = get_control_panel(
                    chat_id=chat_id,
                    is_paused=False,
                    is_looping=queue_manager.is_loop_enabled(chat_id),
                    is_muted=queue_manager.is_muted(chat_id),
                )
                preview_url = next_track.url or next_track.thumbnail
                preview_opts = LinkPreviewOptions(
                    is_disabled=False,
                    url=preview_url,
                    prefer_large_media=True,
                    show_above_text=True,
                ) if preview_url else None

                msg = await RichParser.send(
                    bot_client,
                    chat_id=chat_id,
                    text=text,
                    reply_markup=markup,
                    link_preview_options=preview_opts,
                )
                queue_manager.set_now_playing_msg(chat_id, msg.id)
            except Exception as e:
                logger.error(f"Gagal memutar lagu berikutnya di {chat_id}: {e}")
                await self.leave_call(chat_id)
        elif queue_manager.is_autoplay_enabled(chat_id):
            # Auto-Play: Cari dan putar lagu rekomendasi otomatis
            try:
                last_track = queue_manager.get_last_played_track(chat_id)
                history = queue_manager.get_played_history(chat_id)
                from utils.ytdl import ytdl_helper
                rec_track = await ytdl_helper.get_recommended_track(last_track, history)
                if rec_track:
                    queue_manager.set_current_track(chat_id, rec_track)
                    await self.play_stream(chat_id, rec_track)
                    text = format_now_playing(
                        track=rec_track,
                        current_sec=0,
                        is_paused=False,
                        is_looping=False,
                        volume=queue_manager.get_volume(chat_id),
                        is_muted=queue_manager.is_muted(chat_id),
                    )
                    markup = get_control_panel(
                        chat_id=chat_id,
                        is_paused=False,
                        is_looping=False,
                        is_muted=queue_manager.is_muted(chat_id),
                    )
                    preview_url = rec_track.url or rec_track.thumbnail
                    preview_opts = LinkPreviewOptions(
                        is_disabled=False,
                        url=preview_url,
                        prefer_large_media=True,
                        show_above_text=True,
                    ) if preview_url else None

                    msg = await RichParser.send(
                        bot_client,
                        chat_id=chat_id,
                        text=text,
                        reply_markup=markup,
                        link_preview_options=preview_opts,
                    )
                    queue_manager.set_now_playing_msg(chat_id, msg.id)
                    return
            except Exception as e:
                logger.error(f"Gagal memutar lagu Auto-Play di {chat_id}: {e}")

            await self.leave_call(chat_id)
        else:
            # Tidak ada lagu lagi & Auto-Play mati, tinggalkan Voice Chat
            try:
                await RichParser.send(
                    bot_client,
                    chat_id=chat_id,
                    text=(
                        "| ⏹ Antrean Pemutaran Selesai |\n"
                        "|:---:|\n"
                        "| Seluruh lagu di antrean telah selesai diputar |\n\n"
                        "| Status Sistem | Keterangan |\n"
                        "|:---|:---|\n"
                        "| 🔌 Mode Standby | Bot meninggalkan Voice Chat |\n"
                        "| 💡 Tips | Ketik `/autoplay on` untuk memutar musik tanpa henti |\n\n"
                        "| 🤖 Nusantara Stream 🤖 |\n"
                        "|:---:|\n"
                        "| |"
                    ),
                )
            except Exception:
                pass
            await self.leave_call(chat_id)


call_manager = CallManager()
