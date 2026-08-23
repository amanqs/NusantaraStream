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
import re
from typing import Any, Optional
try:
    import yt_dlp
except ImportError:
    yt_dlp = None

from config import Config
from utils.queue import TrackInfo

logger = logging.getLogger("NusantaraStream.YTDL")

# Opsi standar yt-dlp yang dioptimalkan untuk streaming cepat & anti-blocking
YTDL_BASE_OPTIONS: dict[str, Any] = {
    "format": "bestaudio/best",
    "outtmpl": os.path.join(Config.CACHE_DIR, "%(id)s.%(ext)s"),
    "geo_bypass": True,
    "nocheckcertificate": True,
    "quiet": True,
    "no_warnings": True,
    "source_address": "0.0.0.0",
    "default_search": "ytsearch",
    "prefer_ffmpeg": True,
    "noplaylist": True,
    "extract_flat": False,
    "cachedir": False,
    "http_headers": {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
    },
}

if Config.COOKIES_FILE and os.path.exists(Config.COOKIES_FILE):
    YTDL_BASE_OPTIONS["cookiefile"] = Config.COOKIES_FILE


class YtDlpHelper:
    """Helper yt-dlp asinkron untuk pencarian dan ekstraksi streaming audio/video."""

    URL_REGEX = re.compile(
        r"^(https?://)?(www\.|m\.)?(youtube\.com|youtu\.be|soundcloud\.com|spotify\.com)/.+$"
    )
    SPOTIFY_REGEX = re.compile(
        r"^(https?://)?(open\.)?spotify\.com/(track|album|playlist)/([a-zA-Z0-9]+)"
    )
    SOUNDCLOUD_REGEX = re.compile(
        r"^(https?://)?(www\.|m\.)?(soundcloud\.com|on\.soundcloud\.com)/.+"
    )

    def is_url(self, query: str) -> bool:
        """Cek apakah query merupakan link URL yang valid."""
        return bool(self.URL_REGEX.match(query.strip())) or query.strip().startswith(
            ("http://", "https://")
        )

    def is_spotify(self, query: str) -> bool:
        """Cek apakah query merupakan tautan lagu/playlist Spotify."""
        return bool(self.SPOTIFY_REGEX.search(query.strip())) or "spotify.link" in query.lower()

    def is_soundcloud(self, query: str) -> bool:
        """Cek apakah query merupakan tautan SoundCloud."""
        return bool(self.SOUNDCLOUD_REGEX.search(query.strip()))

    async def resolve_spotify(self, url: str) -> list[dict[str, str]]:
        """Mengekstrak judul & artis dari tautan Spotify publik via oEmbed & Web metadata."""
        import aiohttp
        tracks = []
        try:
            async with aiohttp.ClientSession() as session:
                oembed_url = f"https://open.spotify.com/oembed?url={url}"
                async with session.get(oembed_url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        title = data.get("title", "")
                        author = data.get("author_name", "")
                        thumbnail = data.get("thumbnail_url", "")
                        if title:
                            tracks.append({
                                "title": title,
                                "artist": author,
                                "thumbnail": thumbnail,
                                "query": f"{title} {author}".strip(),
                            })
        except Exception as e:
            logger.error(f"Error resolve Spotify oembed: {e}")

        # Jika URL berupa playlist/album dan oembed tidak menemukan tracklist
        if ("playlist" in url or "album" in url) and not tracks:
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                        if resp.status == 200:
                            html = await resp.text()
                            m_title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
                            m_desc = re.search(r'<meta property="og:description" content="([^"]+)"', html)
                            if m_title:
                                t_name = m_title.group(1)
                                a_name = m_desc.group(1) if m_desc else ""
                                tracks.append({
                                    "title": t_name,
                                    "artist": a_name,
                                    "query": f"{t_name} {a_name}".strip(),
                                })
            except Exception:
                pass

        return tracks

    async def search_youtube(
        self, query: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Mencari daftar video di YouTube berdasarkan keyword secara non-blocking."""
        loop = asyncio.get_running_loop()

        def _search():
            opts = dict(YTDL_BASE_OPTIONS)
            opts["extract_flat"] = "in_playlist"
            with yt_dlp.YoutubeDL(opts) as ydl:
                try:
                    info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
                    if not info or "entries" not in info:
                        return []
                    results = []
                    for entry in info["entries"]:
                        if not entry:
                            continue
                        results.append(
                            {
                                "id": entry.get("id"),
                                "title": entry.get("title", "Tidak Ada Judul"),
                                "duration": entry.get("duration", 0),
                                "duration_string": entry.get("duration_string", "00:00"),
                                "channel": entry.get("uploader")
                                or entry.get("channel", "YouTube"),
                                "url": f"https://www.youtube.com/watch?v={entry.get('id')}",
                                "thumbnail": entry.get("thumbnails", [{}])[0].get("url")
                                if entry.get("thumbnails")
                                else None,
                            }
                        )
                    return results
                except Exception as e:
                    logger.error(f"Error saat mencari YouTube: {e}")
                    return []

        return await loop.run_in_executor(None, _search)

    async def extract_stream(
        self,
        query_or_url: str,
        is_video: bool = False,
        requester_id: int = 0,
        requester_name: str = "Pengguna",
    ) -> Optional[TrackInfo]:
        """Mengekstrak URL stream langsung atau mendownload buffer lagu."""
        loop = asyncio.get_running_loop()

        def _extract():
            opts = dict(YTDL_BASE_OPTIONS)
            if is_video:
                opts["format"] = (
                    "best[height<=720][ext=mp4]/bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best"
                )
            else:
                opts["format"] = "bestaudio/best"

            with yt_dlp.YoutubeDL(opts) as ydl:
                try:
                    target = query_or_url
                    if not self.is_url(target):
                        target = f"ytsearch1:{query_or_url}"

                    info = ydl.extract_info(target, download=False)
                    if not info:
                        return None

                    # Jika hasil adalah search/playlist
                    if "entries" in info:
                        entries = [e for e in info["entries"] if e]
                        if not entries:
                            return None
                        info = entries[0]

                    title = info.get("title", "Audio Stream")
                    webpage_url = info.get("webpage_url") or query_or_url
                    duration = int(info.get("duration") or 0)
                    is_live = bool(info.get("is_live", False))
                    channel = (
                        info.get("uploader")
                        or info.get("channel")
                        or "Nusantara Stream"
                    )

                    # Ambil thumbnail beresolusi terbaik
                    thumbnail = None
                    if "thumbnails" in info and info["thumbnails"]:
                        thumbnail = info["thumbnails"][-1].get("url")
                    elif "thumbnail" in info:
                        thumbnail = info["thumbnail"]

                    # Pilih direct stream URL terbaik
                    stream_url = info.get("url")
                    video_url = None

                    if "formats" in info:
                        formats = info.get("formats", [])
                        if is_video:
                            # 1. Cari video stream format (resolusi <= 720p)
                            video_formats = [
                                f
                                for f in formats
                                if f.get("url")
                                and f.get("vcodec")
                                and f.get("vcodec") != "none"
                                and (f.get("height") or 0) <= 720
                            ]
                            if video_formats:
                                video_url = video_formats[-1].get("url")

                            # 2. Cari audio stream format
                            audio_formats = [
                                f
                                for f in formats
                                if f.get("url")
                                and f.get("acodec")
                                and f.get("acodec") != "none"
                            ]
                            if audio_formats:
                                stream_url = audio_formats[-1].get("url")
                            elif not stream_url and formats:
                                stream_url = formats[-1].get("url")

                            if not video_url:
                                video_url = stream_url
                        else:
                            audio_formats = [
                                f
                                for f in formats
                                if f.get("url")
                                and f.get("acodec")
                                and f.get("acodec") != "none"
                            ]
                            if audio_formats:
                                stream_url = audio_formats[-1].get("url")
                            elif not stream_url and formats:
                                stream_url = formats[-1].get("url")

                    if not stream_url and not video_url:
                        logger.warning(
                            f"Tidak menemukan stream URL langsung untuk: {title}"
                        )
                        return None

                    if is_video and not stream_url:
                        stream_url = video_url

                    return TrackInfo(
                        title=title,
                        url=webpage_url,
                        stream_url=stream_url,
                        video_url=video_url,
                        duration=duration,
                        channel=channel,
                        thumbnail=thumbnail,
                        requested_by_id=requester_id,
                        requested_by_name=requester_name,
                        is_video=is_video,
                        is_live=is_live,
                    )
                except Exception as e:
                    logger.error(f"Gagal mengekstrak info yt-dlp: {e}")
                    return None

        return await loop.run_in_executor(None, _extract)

    async def extract_track_info(self, query_or_url: str) -> Optional[dict[str, Any]]:
        """Mengekstrak metadata info lagu dari keyword atau link URL YouTube."""
        stream_info = await self.extract_stream(query_or_url)
        if stream_info:
            return {
                "id": stream_info.url.split("v=")[-1] if "v=" in stream_info.url else "yt_song",
                "title": stream_info.title,
                "url": stream_info.url,
                "duration": stream_info.duration,
                "channel": stream_info.channel,
                "thumbnail": stream_info.thumbnail,
            }
        search_res = await self.search_youtube(query_or_url, limit=1)
        if search_res:
            return search_res[0]
        return None

    async def get_recommended_track(
        self,
        last_track: Optional[TrackInfo],
        played_history: list[str] = [],
    ) -> Optional[TrackInfo]:
        """Mencari dan mengekstrak lagu rekomendasi otomatis berdasarkan lagu sebelumnya."""
        query = "Top Nusantara Music Hits"
        if last_track and last_track.title:
            # Cari berdasarkan channel atau mix lagu sebelumnya
            clean_chan = re.sub(r" - Topic|VEVO|Official|Channel", "", last_track.channel or "").strip()
            if clean_chan and clean_chan.lower() not in ("youtube", "nusantara stream"):
                query = f"{clean_chan} songs"
            else:
                # Ambil keyword judul lagu
                query = f"{last_track.title} mix"

        search_results = await self.search_youtube(query, limit=8)
        if not search_results:
            search_results = await self.search_youtube("Indonesian pop music hits", limit=5)

        # Filter out lagu yang baru saja diputar
        target_song = None
        for res in search_results:
            t_url = res.get("url", "")
            t_id = res.get("id", "")
            t_title = res.get("title", "")
            if t_url not in played_history and t_id not in played_history and t_title not in played_history:
                target_song = res
                break

        if not target_song and search_results:
            target_song = search_results[0]

        if not target_song:
            return None

        # Ekstrak stream stream_url langsung
        rec_track = await self.extract_stream(
            target_song["url"],
            is_video=False,
            requester_id=0,
            requester_name="Auto-Play 🤖",
        )
        if rec_track:
            rec_track.is_autoplay = True
        return rec_track


ytdl_helper = YtDlpHelper()
