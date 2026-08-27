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
import re
import time
from typing import Optional
import aiohttp

logger = logging.getLogger("NusantaraStream.IPTV")

IPTV_SOURCES = {
    "indonesia": "https://iptv-org.github.io/iptv/countries/id.m3u",
    "news": "https://iptv-org.github.io/iptv/categories/news.m3u",
    "sports": "https://iptv-org.github.io/iptv/categories/sports.m3u",
    "music": "https://iptv-org.github.io/iptv/categories/music.m3u",
    "religious": "https://iptv-org.github.io/iptv/categories/religious.m3u",
    "kids": "https://iptv-org.github.io/iptv/categories/kids.m3u",
}

# Cache: source_key -> {"timestamp": float, "channels": list[dict]}
_CACHE: dict[str, dict] = {}
CACHE_TTL = 21600  # 6 Jam


class IPTVManager:
    """Manajer dan Parser cerdas untuk repositori iptv-org/iptv."""

    @staticmethod
    def parse_m3u(content: str) -> list[dict]:
        """Parsing berkas M3U / M3U8 menjadi daftar metadata saluran TV."""
        channels = []
        lines = [line.strip() for line in content.splitlines() if line.strip()]

        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("#EXTINF:"):
                # Ekstrak metadata tvg
                logo_match = re.search(r'tvg-logo="([^"]+)"', line)
                group_match = re.search(r'group-title="([^"]+)"', line)
                id_match = re.search(r'tvg-id="([^"]+)"', line)

                # Ekstrak nama saluran (setelah koma terakhir)
                title = line.split(",")[-1].strip() if "," in line else "Live Channel"

                logo = logo_match.group(1) if logo_match else ""
                group = group_match.group(1) if group_match else "General"
                tvg_id = id_match.group(1) if id_match else ""

                # Cari URL stream di baris berikutnya (melewati directive #EXTVLCOPT jika ada)
                stream_url = ""
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    if next_line.startswith("http://") or next_line.startswith("https://"):
                        stream_url = next_line
                        i = j
                        break
                    j += 1

                if stream_url:
                    # Buat slug ID unik yang aman untuk Telegram callback_data
                    safe_slug = re.sub(r"[^a-zA-Z0-9_]", "_", title.lower())[:24]
                    channels.append(
                        {
                            "id": safe_slug,
                            "title": title,
                            "url": stream_url,
                            "logo": logo,
                            "group": group,
                            "tvg_id": tvg_id,
                        }
                    )
            i += 1
        return channels

    @classmethod
    async def fetch_channels(cls, category: str = "indonesia") -> list[dict]:
        """Mengambil dan mem-parsing daftar saluran TV dari iptv-org dengan caching."""
        source_url = IPTV_SOURCES.get(category, IPTV_SOURCES["indonesia"])
        now = time.time()

        # Gunakan cache jika masih valid
        if category in _CACHE:
            entry = _CACHE[category]
            if now - entry.get("timestamp", 0) < CACHE_TTL and entry.get("channels"):
                return entry["channels"]

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(source_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        channels = cls.parse_m3u(text)
                        if channels:
                            _CACHE[category] = {
                                "timestamp": now,
                                "channels": channels,
                            }
                            logger.info(f"Berhasil memuat {len(channels)} saluran IPTV untuk kategori '{category}'.")
                            return channels
        except Exception as e:
            logger.error(f"Gagal mengambil playlist IPTV untuk '{category}': {e}")

        # Fallback ke cache kadaluarsa jika ada error jaringan
        if category in _CACHE and _CACHE[category].get("channels"):
            return _CACHE[category]["channels"]

        return []

    @classmethod
    async def search_channel(cls, query_str: str) -> list[dict]:
        """Mencari saluran TV berdasarkan kata kunci di playlist Indonesia & Global."""
        query_lower = query_str.lower().strip()
        all_channels = await cls.fetch_channels("indonesia")

        # Jika hasil pencarian lokal sedikit, gabungkan dengan kategori berita/olahraga
        if len(query_lower) >= 2:
            news_ch = await cls.fetch_channels("news")
            sports_ch = await cls.fetch_channels("sports")
            combined = all_channels + news_ch + sports_ch
        else:
            combined = all_channels

        # Deduplikasi berdasarkan URL
        seen_urls = set()
        unique_list = []
        for ch in combined:
            if ch["url"] not in seen_urls:
                seen_urls.add(ch["url"])
                unique_list.append(ch)

        # Filter pencarian
        matches = [
            ch for ch in unique_list
            if query_lower in ch["title"].lower() or query_lower in ch["group"].lower()
        ]
        return matches[:15]


iptv_manager = IPTVManager()
