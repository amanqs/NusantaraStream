# ==============================================================================
#  🇮🇩 Nusantara Stream - Telegram Music & Video Streaming Bot
# ==============================================================================
#  Author   : Amang (@BukanDevelopers)
#  GitHub   : https://github.com/amanqs
#  Project  : Nusantara Stream Telegram Bot
#  License  : GNU General Public License v3.0
# ==============================================================================

import asyncio
import os
from io import BytesIO
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config import Config
from utils.formatters import get_readable_time


def _get_font(size: int, bold: bool = False):
    """Load standard system TTF font."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf" if bold else "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


async def _download_thumbnail(url: str) -> Image.Image:
    """Download and return PIL Image from URL or create fallback."""
    if not url:
        return _create_fallback_thumb()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=6)) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    return Image.open(BytesIO(data)).convert("RGBA")
    except Exception:
        pass
    return _create_fallback_thumb()


def _create_fallback_thumb() -> Image.Image:
    """Create default music artwork."""
    img = Image.new("RGBA", (280, 180), color=(15, 23, 42, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (280, 180)], fill=(30, 41, 59))
    font = _get_font(22, bold=True)
    draw.text((140, 90), "🎵 NUSANTARA", fill=(248, 250, 252), font=font, anchor="mm")
    return img


def _draw_rounded_rect(draw: ImageDraw.ImageDraw, coords, radius: int, fill, outline=None, width: int = 1):
    """Draw a rounded rectangle."""
    draw.rounded_rectangle(coords, radius=radius, fill=fill, outline=outline, width=width)


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, max_lines: int = 4) -> list[str]:
    """Wrap long text into multiple lines fitting max_width."""
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = font.getbbox(test_line)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
            if len(lines) >= max_lines - 1:
                break

    if current_line and len(lines) < max_lines:
        lines.append(current_line)

    # Add ellipsis if truncated
    if len(lines) == max_lines and len(words) > len(" ".join(lines).split()):
        if not lines[-1].endswith("..."):
            lines[-1] = lines[-1][: max(0, len(lines[-1]) - 3)] + "..."

    return lines or [text]


def generate_now_playing_card(
    title: str,
    channel: str,
    duration: int,
    is_video: bool,
    is_live: bool,
    requester_name: str,
    thumb_img: Image.Image,
    chat_id: int,
) -> str:
    """Generate the exact Now Playing Card matching the Kalena/NavyDevs reference screenshot."""
    W, H = 640, 850
    img = Image.new("RGBA", (W, H), color=(14, 23, 38, 255))
    draw = ImageDraw.Draw(img)

    # Background gradient
    for y in range(H):
        r = int(14 + (y / H) * 12)
        g = int(24 + (y / H) * 18)
        b = int(42 + (y / H) * 22)
        draw.line([(0, y), (W, y)], fill=(r, g, b, 255))

    # Fonts
    font_title = _get_font(21, bold=True)
    font_by = _get_font(14, bold=False)
    font_np = _get_font(11, bold=True)
    font_header_box = _get_font(16, bold=True)
    font_table_hdr = _get_font(16, bold=True)
    font_table_label = _get_font(14, bold=True)
    font_table_val = _get_font(14, bold=False)
    font_footer = _get_font(14, bold=True)

    # 1. TOP SECTION: Thumbnail + Title + Equalizer
    top_y = 28
    thumb_w, thumb_h = 240, 150
    thumb_resized = thumb_img.resize((thumb_w, thumb_h), Image.LANCZOS)

    # Mask rounded corners for thumbnail
    mask = Image.new("L", (thumb_w, thumb_h), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([(0, 0), (thumb_w, thumb_h)], radius=12, fill=255)
    img.paste(thumb_resized, (25, top_y), mask)

    # Outer border for thumbnail
    draw.rounded_rectangle([(25, top_y), (25 + thumb_w, top_y + thumb_h)], radius=12, outline=(56, 189, 248, 200), width=2)

    # Metadata on Right
    meta_x = 282
    meta_w = W - meta_x - 25

    clean_short_title = title.upper()
    wrapped_top_title = _wrap_text(clean_short_title, font_title, meta_w, max_lines=2)
    cur_y = top_y + 4
    for l in wrapped_top_title:
        draw.text((meta_x, cur_y), l, fill=(248, 250, 252), font=font_title)
        cur_y += 25

    draw.text((meta_x, cur_y + 3), f"By {requester_name}", fill=(148, 163, 184), font=font_by)

    # Equalizer Waveform Bars (Vertical gradient bars)
    wave_y = cur_y + 30
    bar_heights = [12, 24, 16, 34, 22, 38, 28, 42, 32, 26, 40, 20, 36, 18, 28, 14, 24, 10]
    bar_x = meta_x
    bar_w = 5
    bar_gap = 4

    colors = [
        (56, 189, 248),  # Sky blue
        (96, 165, 250),  # Blue
        (129, 140, 248), # Indigo
        (168, 85, 247),  # Purple
        (217, 70, 239),  # Magenta
        (244, 114, 182), # Rose
    ]

    for i, bh in enumerate(bar_heights):
        c = colors[i % len(colors)]
        by1 = wave_y + (44 - bh) // 2
        by2 = by1 + bh
        draw.rounded_rectangle([(bar_x, by1), (bar_x + bar_w, by2)], radius=3, fill=c)
        bar_x += bar_w + bar_gap

    # NOW PLAYING • KALENA / NUSANTARA
    draw.text((meta_x, wave_y + 58), f"NOW PLAYING • {Config.BOT_NAME.upper()}", fill=(203, 213, 225), font=font_np)

    # 2. MIDDLE SECTION: Capsule "🔴 Media Sedang Diputar"
    box_x = 22
    box_w = W - 44
    cur_box_y = 205

    _draw_rounded_rect(draw, [(box_x, cur_box_y), (box_x + box_w, cur_box_y + 46)], radius=8, fill=(21, 48, 82, 230), outline=(42, 108, 178, 255), width=2)
    # Red status dot + text
    draw.ellipse([(box_x + (box_w // 2) - 105, cur_box_y + 17), (box_x + (box_w // 2) - 93, cur_box_y + 29)], fill=(239, 68, 68))
    draw.text((box_x + (box_w // 2) - 82, cur_box_y + 13), "Media Sedang Diputar", fill=(248, 250, 252), font=font_header_box)

    # 3. MAIN TABLE CARD (2 Columns with Grid Lines)
    tbl_y = cur_box_y + 58
    tbl_h = 495

    # Table outer container
    _draw_rounded_rect(draw, [(box_x, tbl_y), (box_x + box_w, tbl_y + tbl_h)], radius=8, fill=(17, 38, 66, 220), outline=(42, 108, 178, 255), width=2)

    col1_w = 180
    col2_x = box_x + col1_w
    col2_w = box_w - col1_w

    # Table Header (Parameter | Detail Informasi)
    hdr_h = 46
    draw.rectangle([(box_x + 1, tbl_y + 1), (box_x + box_w - 1, tbl_y + hdr_h)], fill=(26, 60, 105, 255))
    draw.line([(box_x, tbl_y + hdr_h), (box_x + box_w, tbl_y + hdr_h)], fill=(42, 108, 178, 255), width=2)
    draw.line([(col2_x, tbl_y), (col2_x, tbl_y + tbl_h)], fill=(42, 108, 178, 255), width=2)

    draw.text((box_x + 40, tbl_y + 13), "Parameter", fill=(224, 242, 254), font=font_table_hdr)
    draw.text((col2_x + 85, tbl_y + 13), "Detail Informasi", fill=(224, 242, 254), font=font_table_hdr)

    # Row 1: Judul Media (Height: 200)
    row1_y = tbl_y + hdr_h
    row1_h = 200
    draw.line([(box_x, row1_y + row1_h), (box_x + box_w, row1_y + row1_h)], fill=(42, 108, 178, 255), width=1)

    # Judul Media Icon & Label
    draw.polygon([(box_x + 18, row1_y + 24), (box_x + 18, row1_y + 38), (box_x + 30, row1_y + 31)], fill=(56, 189, 248))
    draw.text((box_x + 38, row1_y + 22), "Judul Media", fill=(241, 245, 249), font=font_table_label)

    # Judul Media Value (Wrapped)
    title_lines = _wrap_text(title.upper(), font_table_val, col2_w - 30, max_lines=6)
    t_y = row1_y + 22
    for line in title_lines:
        draw.text((col2_x + 16, t_y), line, fill=(226, 232, 240), font=font_table_val)
        t_y += 26

    # Row 2: Format Stream (Height: 80)
    row2_y = row1_y + row1_h
    row2_h = 80
    draw.line([(box_x, row2_y + row2_h), (box_x + box_w, row2_y + row2_h)], fill=(42, 108, 178, 255), width=1)

    # Format Stream Icon & Label
    draw.rectangle([(box_x + 18, row2_y + 28), (box_x + 32, row2_y + 44)], fill=(14, 165, 233))
    draw.text((box_x + 38, row2_y + 28), "Format Stream", fill=(241, 245, 249), font=font_table_label)

    # Format Stream Value
    stream_str = "Video (HD)" if is_video else "Audio"
    draw.ellipse([(col2_x + 16, row2_y + 28), (col2_x + 32, row2_y + 44)], fill=(56, 189, 248), outline=(224, 242, 254), width=2)
    draw.text((col2_x + 40, row2_y + 28), stream_str, fill=(226, 232, 240), font=font_table_val)

    # Row 3: Diminta oleh (Height: 80)
    row3_y = row2_y + row2_h
    row3_h = 80
    draw.line([(box_x, row3_y + row3_h), (box_x + box_w, row3_y + row3_h)], fill=(42, 108, 178, 255), width=1)

    # Diminta oleh Icon & Label
    draw.ellipse([(box_x + 20, row3_y + 26), (box_x + 32, row3_y + 38)], fill=(168, 85, 247))
    draw.text((box_x + 38, row3_y + 28), "Diminta oleh", fill=(241, 245, 249), font=font_table_label)

    # Diminta oleh Value
    draw.text((col2_x + 16, row3_y + 28), requester_name, fill=(226, 232, 240), font=font_table_val)

    # Row 4: Total Durasi (Height: 90)
    row4_y = row3_y + row3_h
    # Total Durasi Icon & Label
    draw.ellipse([(box_x + 18, row4_y + 30), (box_x + 34, row4_y + 46)], outline=(251, 191, 36), width=2)
    draw.text((box_x + 38, row4_y + 30), "Total Durasi", fill=(241, 245, 249), font=font_table_label)

    # Total Durasi Value
    dur_str = "Live Streaming" if is_live else get_readable_time(duration)
    draw.text((col2_x + 16, row4_y + 30), dur_str, fill=(226, 232, 240), font=font_table_val)

    # 4. BOTTOM SECTION: Footer Capsule Box
    foot_y = tbl_y + tbl_h + 14
    _draw_rounded_rect(draw, [(box_x, foot_y), (box_x + box_w, foot_y + 46)], radius=8, fill=(21, 48, 82, 230), outline=(42, 108, 178, 255), width=2)

    footer_text = "💡 NavyDevs Core & R2YS [v2.7] ⚡ © 2026"
    draw.text((box_x + (box_w // 2), foot_y + 14), footer_text, fill=(248, 250, 252), font=font_footer, anchor="mt")

    # Save image
    os.makedirs(Config.CACHE_DIR, exist_ok=True)
    out_path = os.path.join(Config.CACHE_DIR, f"nowplaying_{chat_id}.png")
    img.save(out_path, format="PNG")
    return out_path


async def get_now_playing_card_path(track, chat_id: int) -> str:
    """Async helper to generate and return the Now Playing card image path."""
    thumb = await _download_thumbnail(track.thumbnail)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        generate_now_playing_card,
        track.title,
        track.channel or "YouTube",
        track.duration,
        track.is_video,
        track.is_live,
        track.requested_by_name or "Pengguna",
        thumb,
        chat_id,
    )
