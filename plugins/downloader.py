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
import aiohttp
import aiofiles

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

try:
    from kurigram import Client, filters
    from kurigram.types import Message, LinkPreviewOptions, ReplyParameters
    from kurigram.enums import ParseMode
except ImportError:
    from pyrogram import Client, filters
    from pyrogram.types import Message, LinkPreviewOptions, ReplyParameters
    from pyrogram.enums import ParseMode

from config import Config
from utils.ytdl import YTDL_BASE_OPTIONS, ytdl_helper
from utils.formatters import clean_markdown, get_readable_time, human_readable_size
from utils.rich_parser import RichParser
from utils.decorators import BOT

logger = logging.getLogger("NusantaraStream.Downloader")


async def download_thumbnail(thumb_url: str, output_path: str) -> str | None:
    """Mengunduh gambar thumbnail ke lokal disk dan mengonversinya ke format JPEG standar Telegram."""
    if not thumb_url:
        return None
    try:
        raw_path = output_path + ".raw"
        async with aiohttp.ClientSession() as session:
            async with session.get(thumb_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    async with aiofiles.open(raw_path, "wb") as f:
                        await f.write(await resp.read())

                    try:
                        from PIL import Image
                        with Image.open(raw_path) as img:
                            rgb_img = img.convert("RGB")
                            rgb_img.save(output_path, "JPEG", quality=95)
                        if os.path.exists(raw_path):
                            os.remove(raw_path)
                        return output_path
                    except Exception as pe:
                        logger.debug(f"Pillow convert error: {pe}")
                        if os.path.exists(raw_path):
                            os.rename(raw_path, output_path)
                        return output_path
    except Exception as e:
        logger.debug(f"Gagal unduh thumbnail: {e}")
    return None


def tag_mp3_metadata(file_path: str, title: str, artist: str, thumb_path: str = None):
    """Menyematkan ID3 metadata (judul, artis, album art) ke file MP3 menggunakan mutagen."""
    try:
        import mutagen
        from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, ID3NoHeaderError

        try:
            audio = ID3(file_path)
        except ID3NoHeaderError:
            audio = ID3()

        audio.add(TIT2(encoding=3, text=title))
        audio.add(TPE1(encoding=3, text=artist))
        audio.add(TALB(encoding=3, text="Nusantara Stream"))

        if thumb_path and os.path.exists(thumb_path):
            with open(thumb_path, "rb") as img:
                audio.add(
                    APIC(
                        encoding=3,
                        mime="image/jpeg",
                        type=3,
                        desc="Cover",
                        data=img.read(),
                    )
                )
        audio.save(file_path)
    except Exception as e:
        logger.debug(f"Mutagen tagging error: {e}")


@BOT("song", "mp3", "music")
async def song_downloader_command(client: Client, message: Message):
    """Handler perintah /song untuk mengunduh lagu MP3 dari YouTube langsung ke Telegram."""
    if len(message.command) < 2:
        return await RichParser.reply(
            message,
            "ℹ️ **Format Penggunaan:**\n"
            "> `/song [Judul Lagu / URL YouTube]`\n\n"
            "*Contoh:* `/song Indonesia Raya`"
        )

    query = message.text.split(None, 1)[1].strip()
    status_msg = await RichParser.reply(
        message,
        f"🔍 *Mencari & menyiapkan berkas audio untuk:* `{clean_markdown(query)}`..."
    )

    loop = asyncio.get_running_loop()

    def _download_song():
        out_tmpl = os.path.join(Config.TEMP_DIR, "%(id)s_song.%(ext)s")
        opts = dict(YTDL_BASE_OPTIONS)
        opts.update(
            {
                "format": "bestaudio/best",
                "outtmpl": out_tmpl,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "320",
                    }
                ],
            }
        )

        with yt_dlp.YoutubeDL(opts) as ydl:
            target = query if ytdl_helper.is_url(query) else f"ytsearch1:{query}"
            info = ydl.extract_info(target, download=True)
            if "entries" in info:
                info = info["entries"][0]

            vid_id = info.get("id")
            title = info.get("title", "Lagu Nusantara")
            duration = int(info.get("duration") or 0)
            channel = info.get("uploader") or info.get("channel") or "Nusantara Stream"
            thumb = info.get("thumbnail") or (info["thumbnails"][-1]["url"] if info.get("thumbnails") else None)

            mp3_path = os.path.join(Config.TEMP_DIR, f"{vid_id}_song.mp3")
            return {
                "file_path": mp3_path,
                "title": title,
                "duration": duration,
                "channel": channel,
                "thumbnail": thumb,
                "id": vid_id,
            }

    try:
        song_info = await loop.run_in_executor(None, _download_song)
        mp3_path = song_info["file_path"]

        if not os.path.exists(mp3_path):
            return await RichParser.edit(status_msg, "❌ *Gagal mengunduh berkas audio dari YouTube.*")

        await RichParser.edit(status_msg, "📤 *Sedang mengunggah audio ke Telegram...*")

        # Download thumbnail & embed metadata
        thumb_file = os.path.join(Config.TEMP_DIR, f"{song_info['id']}_thumb.jpg")
        thumb_path = await download_thumbnail(song_info["thumbnail"], thumb_file)
        
        tag_mp3_metadata(mp3_path, song_info["title"], song_info["channel"], thumb_path)

        s_title = clean_markdown(song_info["title"])
        s_channel = clean_markdown(song_info["channel"])

        # Format Caption 1 Pesan (Blockquote Native)
        caption_card = (
            f"🎵 **{s_title}**\n\n"
            f"> 👤 **Artis:** `{s_channel}`\n"
            f"> ⏱ **Durasi:** `{get_readable_time(song_info['duration'])}`\n"
            f"> 💾 **Ukuran:** `{human_readable_size(os.path.getsize(mp3_path))}`\n"
            f"> 🎧 **Format:** `MP3 320kbps Audio`\n\n"
            f"🤖 *Diunduh via {Config.BOT_NAME}*"
        )

        # Kirim Audio dan Caption dalam 1 Pesan
        await client.send_audio(
            chat_id=message.chat.id,
            audio=mp3_path,
            title=song_info["title"],
            performer=song_info["channel"],
            duration=song_info["duration"],
            thumb=thumb_path if thumb_path and os.path.exists(thumb_path) else None,
            caption=caption_card,
            reply_parameters=ReplyParameters(message_id=message.id),
        )
        
        await status_msg.delete()

        # Bersihkan file temp
        for path in [mp3_path, thumb_file]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"Error pada /song: {e}")
        await RichParser.edit(status_msg, f"❌ **Gagal:** `{clean_markdown(str(e))}`")


@BOT("video", "mp4", "vdownload")
async def video_downloader_command(client: Client, message: Message):
    """Handler perintah /video untuk mengunduh video MP4 dari YouTube langsung ke Telegram."""
    if len(message.command) < 2:
        return await RichParser.reply(
            message,
            "ℹ️ **Format Penggunaan:**\n"
            "> `/video [Judul Video / URL YouTube]`\n\n"
            "*Contoh:* `/video Indonesia Raya HD`"
        )

    query = message.text.split(None, 1)[1].strip()
    status_msg = await RichParser.reply(
        message,
        f"🔍 *Mencari & menyiapkan berkas video untuk:* `{clean_markdown(query)}`..."
    )

    loop = asyncio.get_running_loop()

    def _download_video():
        out_tmpl = os.path.join(Config.TEMP_DIR, "%(id)s_vid.%(ext)s")
        opts = dict(YTDL_BASE_OPTIONS)
        opts.update(
            {
                "format": "best[height<=720][ext=mp4]/best[ext=mp4]/best",
                "outtmpl": out_tmpl,
            }
        )

        with yt_dlp.YoutubeDL(opts) as ydl:
            target = query if ytdl_helper.is_url(query) else f"ytsearch1:{query}"
            info = ydl.extract_info(target, download=True)
            if "entries" in info:
                info = info["entries"][0]

            vid_id = info.get("id")
            title = info.get("title", "Video Nusantara")
            duration = int(info.get("duration") or 0)
            channel = info.get("uploader") or info.get("channel") or "Nusantara Stream"
            thumb = info.get("thumbnail") or (info["thumbnails"][-1]["url"] if info.get("thumbnails") else None)

            vid_path = os.path.join(Config.TEMP_DIR, f"{vid_id}_vid.mp4")
            return {
                "file_path": vid_path,
                "title": title,
                "duration": duration,
                "channel": channel,
                "thumbnail": thumb,
                "id": vid_id,
            }

    try:
        vid_info = await loop.run_in_executor(None, _download_video)
        vid_path = vid_info["file_path"]

        if not os.path.exists(vid_path):
            return await RichParser.edit(status_msg, "❌ *Gagal mengunduh berkas video dari YouTube.*")

        await RichParser.edit(status_msg, "📤 *Sedang mengunggah video ke Telegram...*")

        thumb_file = os.path.join(Config.TEMP_DIR, f"{vid_info['id']}_thumb.jpg")
        thumb_path = await download_thumbnail(vid_info["thumbnail"], thumb_file)

        v_title = clean_markdown(vid_info["title"])
        v_channel = clean_markdown(vid_info["channel"])

        # Format Caption 1 Pesan (Blockquote Native)
        caption_card = (
            f"🎬 **{v_title}**\n\n"
            f"> 📺 **Channel:** `{v_channel}`\n"
            f"> ⏱ **Durasi:** `{get_readable_time(vid_info['duration'])}`\n"
            f"> 💾 **Ukuran:** `{human_readable_size(os.path.getsize(vid_path))}`\n"
            f"> 📹 **Kualitas:** `HD 720p MP4 Video`\n\n"
            f"🤖 *Diunduh via {Config.BOT_NAME}*"
        )

        # Kirim Video dan Caption dalam 1 Pesan
        await client.send_video(
            chat_id=message.chat.id,
            video=vid_path,
            duration=vid_info["duration"],
            thumb=thumb_path if thumb_path and os.path.exists(thumb_path) else None,
            caption=caption_card,
            reply_parameters=ReplyParameters(message_id=message.id),
        )
        
        await status_msg.delete()

        # Bersihkan file temp
        for path in [vid_path, thumb_file]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"Error pada /video: {e}")
        await RichParser.edit(status_msg, f"❌ **Gagal:** `{clean_markdown(str(e))}`")