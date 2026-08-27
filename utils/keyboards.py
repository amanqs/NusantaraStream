# ==============================================================================
#  🇮🇩 Nusantara Stream - Telegram Music & Video Streaming Bot
# ==============================================================================
#  Author   : Amang (@BukanDevelopers)
#  GitHub   : https://github.com/amanqs
#  Project  : Nusantara Stream Telegram Bot
#  License  : GNU General Public License v3.0
# ==============================================================================

try:
    from kurigram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from kurigram.enums import ButtonStyle
except ImportError:
    try:
        from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        from pyrogram.enums import ButtonStyle
    except ImportError:
        class ButtonStyle:
            DEFAULT = "default"
            PRIMARY = "primary"
            DANGER = "danger"
            SUCCESS = "success"

        class InlineKeyboardButton:
            def __init__(
                self, text: str, callback_data: str = "", url: str = "", style=None
            ):
                self.text = text
                self.callback_data = callback_data
                self.url = url
                self.style = style

        class InlineKeyboardMarkup:
            def __init__(self, inline_keyboard: list):
                self.inline_keyboard = inline_keyboard

from config import Config


def resolve_style(style_input=None, text: str = "") -> ButtonStyle:
    """Helper cerdas untuk menentukan ButtonStyle secara proporsional dan harmonis."""
    if isinstance(style_input, ButtonStyle):
        return style_input
    if isinstance(style_input, str):
        s = style_input.lower()
        if s in ("primary", "blue", "utama"):
            return ButtonStyle.PRIMARY
        elif s in ("success", "green", "hijau", "aktif"):
            return ButtonStyle.SUCCESS
        elif s in ("danger", "red", "merah", "peringatan"):
            return ButtonStyle.DANGER
        elif s in ("default", "biasa", "netral"):
            return ButtonStyle.DEFAULT

    # Deteksi otomatis berbasis konteks teks
    t = text.lower()
    if any(k in t for k in ("stop", "tutup", "close", "batal", "cancel", "hapus", "delete")):
        return ButtonStyle.DANGER
    elif any(k in t for k in ("resume", "loop: on", "aktif", "ya", "yes", "setuju")):
        return ButtonStyle.SUCCESS
    elif any(k in t for k in ("play", "pause", "skip", "next", "prev", "tambah", "join", "panduan", "antrean", "player")):
        return ButtonStyle.PRIMARY
    return ButtonStyle.DEFAULT


def get_control_panel(
    chat_id: int,
    is_paused: bool = False,
    is_looping: bool = False,
    is_muted: bool = False,
) -> InlineKeyboardMarkup:
    """Control Panel interaktif 4 baris sesuai persis dengan referensi UI."""
    pause_resume_text = "▶️ Resume" if is_paused else "⏸ Pause"
    pause_resume_cb = f"ctrl:resume:{chat_id}" if is_paused else f"ctrl:pause:{chat_id}"

    mute_text = "🔊 Unmute" if is_muted else "🔇 Mute"
    mute_cb = f"ctrl:unmute:{chat_id}" if is_muted else f"ctrl:mute:{chat_id}"

    loop_text = "🔁 Loop (ON)" if is_looping else "🔁 Loop"
    loop_style = ButtonStyle.SUCCESS if is_looping else ButtonStyle.PRIMARY

    keyboard = [
        # Baris 1: ⏸ Pause | ⛔ Stop | 🔇 Mute (Danger / Reddish)
        [
            InlineKeyboardButton(
                pause_resume_text,
                callback_data=pause_resume_cb,
                style=ButtonStyle.DANGER,
            ),
            InlineKeyboardButton(
                "⛔ Stop",
                callback_data=f"ctrl:stop:{chat_id}",
                style=ButtonStyle.DANGER,
            ),
            InlineKeyboardButton(
                mute_text,
                callback_data=mute_cb,
                style=ButtonStyle.DANGER,
            ),
        ],
        # Baris 2: 📦 Queue (Full Width Green / SUCCESS)
        [
            InlineKeyboardButton(
                "📦 Queue",
                callback_data=f"ctrl:queue:1:{chat_id}",
                style=ButtonStyle.SUCCESS,
            ),
        ],
        # Baris 3: ⏩ Skip | 🔄 Shuffle | 🔁 Loop (Primary / Blue)
        [
            InlineKeyboardButton(
                "⏩ Skip",
                callback_data=f"ctrl:skip:{chat_id}",
                style=ButtonStyle.PRIMARY,
            ),
            InlineKeyboardButton(
                "🔄 Shuffle",
                callback_data=f"ctrl:shuffle:{chat_id}",
                style=ButtonStyle.PRIMARY,
            ),
            InlineKeyboardButton(
                loop_text,
                callback_data=f"ctrl:loop:{chat_id}",
                style=loop_style,
            ),
        ],
        # Baris 4: 🗑 Close (Full Width Red / DANGER)
        [
            InlineKeyboardButton(
                "🗑 Close",
                callback_data=f"ctrl:close:{chat_id}",
                style=ButtonStyle.DANGER,
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_tv_control_panel(
    chat_id: int,
    category: str = "indonesia",
    current_idx: int = 0,
    is_paused: bool = False,
    is_muted: bool = False,
) -> InlineKeyboardMarkup:
    """Control Panel khusus siaran TV & IPTV dengan tombol gonta-ganti channel instan."""
    pause_resume_text = "▶️ Resume" if is_paused else "⏸ Pause"
    pause_resume_cb = f"ctrl:resume:{chat_id}" if is_paused else f"ctrl:pause:{chat_id}"
    mute_text = "🔊 Unmute" if is_muted else "🔇 Mute"
    mute_cb = f"ctrl:unmute:{chat_id}" if is_muted else f"ctrl:mute:{chat_id}"

    prev_idx = max(0, current_idx - 1)
    next_idx = current_idx + 1

    keyboard = [
        # Baris 1: ⏸ Pause | ⛔ Stop | 🔇 Mute
        [
            InlineKeyboardButton(
                pause_resume_text,
                callback_data=pause_resume_cb,
                style=ButtonStyle.DANGER,
            ),
            InlineKeyboardButton(
                "⛔ Stop",
                callback_data=f"ctrl:stop:{chat_id}",
                style=ButtonStyle.DANGER,
            ),
            InlineKeyboardButton(
                mute_text,
                callback_data=mute_cb,
                style=ButtonStyle.DANGER,
            ),
        ],
        # Baris 2: 📺 Ganti Saluran / Buka Daftar TV
        [
            InlineKeyboardButton(
                "📺 Ganti Saluran / Daftar TV",
                callback_data=f"tv_cat:{category}:1",
                style=ButtonStyle.SUCCESS,
            ),
        ],
        # Baris 3: ⬅️ Saluran Sebelumnya | Saluran Berikutnya ➡️
        [
            InlineKeyboardButton(
                "⏮ Saluran Sebelumnya",
                callback_data=f"tv_p:{category}:{prev_idx}",
                style=ButtonStyle.PRIMARY,
            ),
            InlineKeyboardButton(
                "Saluran Berikutnya ⏭",
                callback_data=f"tv_p:{category}:{next_idx}",
                style=ButtonStyle.PRIMARY,
            ),
        ],
        # Baris 4: 🗑 Tutup Panel
        [
            InlineKeyboardButton(
                "🗑 Tutup Panel",
                callback_data=f"ctrl:close:{chat_id}",
                style=ButtonStyle.DANGER,
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_search_carousel_keyboard(
    current_idx: int,
    total_results: int,
    user_id: int,
) -> InlineKeyboardMarkup:
    """Membuat tombol navigasi geser (carousel) dan pilihan format Audio/Video."""
    nav_row = []

    # Tombol Geser Sebelumnya (jika bukan item pertama)
    if current_idx > 0:
        nav_row.append(
            InlineKeyboardButton(
                "⬅️ Sebelumnya",
                callback_data=f"search_nav:{current_idx - 1}:{user_id}",
                style=ButtonStyle.PRIMARY,
            )
        )

    # Indikator Posisi Halaman
    nav_row.append(
        InlineKeyboardButton(
            f"📄 {current_idx + 1}/{total_results}",
            callback_data="noop",
            style=ButtonStyle.DEFAULT,
        )
    )

    # Tombol Geser Berikutnya (jika bukan item terakhir)
    if current_idx < total_results - 1:
        nav_row.append(
            InlineKeyboardButton(
                "Berikutnya ➡️",
                callback_data=f"search_nav:{current_idx + 1}:{user_id}",
                style=ButtonStyle.PRIMARY,
            )
        )

    keyboard = [
        # Baris 1: Navigasi Geser (Carousel Slider)
        nav_row,
        # Baris 2: Pilihan Format Putar (Audio HQ vs Video HD)
        [
            InlineKeyboardButton(
                "🎵 Putar Audio",
                callback_data=f"play_select:{current_idx}:{user_id}:a",
                style=ButtonStyle.SUCCESS,
            ),
            InlineKeyboardButton(
                "🎬 Putar Video",
                callback_data=f"play_select:{current_idx}:{user_id}:v",
                style=ButtonStyle.PRIMARY,
            ),
        ],
        # Baris 3: Batalkan Pencarian
        [
            InlineKeyboardButton(
                "❌ Batalkan Pencarian",
                callback_data=f"cancel_search:{user_id}",
                style=ButtonStyle.DANGER,
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_search_keyboard(
    results: list,
    user_id: int,
    is_video: bool = False,
) -> InlineKeyboardMarkup:
    """Membuat tombol pilihan 1-5 untuk hasil pencarian YouTube (kompatibilitas)."""
    return get_search_carousel_keyboard(0, len(results), user_id)


def get_queue_keyboard(
    chat_id: int,
    current_page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    """Membuat tombol navigasi halaman antrean musik dengan ButtonStyle elegan."""
    nav_buttons = []

    if current_page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                "⬅️ Sebelumnya",
                callback_data=f"ctrl:queue:{current_page - 1}:{chat_id}",
                style=ButtonStyle.PRIMARY,
            )
        )

    nav_buttons.append(
        InlineKeyboardButton(
            f"📄 {current_page}/{total_pages}",
            callback_data="noop",
            style=ButtonStyle.DEFAULT,
        )
    )

    if current_page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(
                "Berikutnya ➡️",
                callback_data=f"ctrl:queue:{current_page + 1}:{chat_id}",
                style=ButtonStyle.PRIMARY,
            )
        )

    keyboard = [
        nav_buttons,
        [
            InlineKeyboardButton(
                "🔙 Kembali ke Player",
                callback_data=f"ctrl:player:{chat_id}",
                style=ButtonStyle.PRIMARY,
            ),
            InlineKeyboardButton(
                "🗑 Tutup Antrean",
                callback_data=f"ctrl:close:{chat_id}",
                style=ButtonStyle.DANGER,
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_start_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    """Membuat tombol menu utama di /start dengan ButtonStyle rapi, modern & proporsional."""
    keyboard = [
        # Baris 1: Tambahkan ke Grup (Full Width Green / SUCCESS)
        [
            InlineKeyboardButton(
                "➕ Tambahkan ke Grup Anda",
                url=f"https://t.me/{bot_username}?startgroup=true",
                style=ButtonStyle.SUCCESS,
            )
        ],
        # Baris 2: Panduan & Perintah (Full Width Blue / PRIMARY)
        [
            InlineKeyboardButton(
                "📖 Panduan & Perintah",
                callback_data="help:main",
                style=ButtonStyle.PRIMARY,
            ),
        ],
        # Baris 3: Informasi Komunitas & Developer (Default Neutral)
        [
            InlineKeyboardButton(
                "💬 Saluran Update",
                url="https://t.me/Telegram",
                style=ButtonStyle.DEFAULT,
            ),
            InlineKeyboardButton(
                "👨‍💻 Source Code",
                url="https://github.com",
                style=ButtonStyle.DEFAULT,
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_help_keyboard(current_tab: str = "main") -> InlineKeyboardMarkup:
    """Membuat navigasi menu bantuan berbasis tab callback dengan ButtonStyle dinamis & terorganisir."""
    music_style = ButtonStyle.SUCCESS if current_tab == "music" else ButtonStyle.PRIMARY
    video_style = ButtonStyle.SUCCESS if current_tab == "video" else ButtonStyle.PRIMARY
    eff_style = ButtonStyle.SUCCESS if current_tab == "effects" else ButtonStyle.PRIMARY
    admin_style = ButtonStyle.SUCCESS if current_tab == "admin" else ButtonStyle.PRIMARY
    sudo_style = ButtonStyle.SUCCESS if current_tab == "sudo" else ButtonStyle.PRIMARY
    info_style = ButtonStyle.SUCCESS if current_tab == "info" else ButtonStyle.PRIMARY

    back_cb = "help:back_start" if current_tab == "main" else "help:main"
    back_label = "🔙 Menu Utama" if current_tab == "main" else "🔙 Panduan Utama"

    keyboard = [
        # Baris 1: Media Utama
        [
            InlineKeyboardButton(
                "🎵 Musik & Audio",
                callback_data="help:music",
                style=music_style,
            ),
            InlineKeyboardButton(
                "🎬 Video Stream",
                callback_data="help:video",
                style=video_style,
            ),
        ],
        # Baris 2: Efek Suara & Admin Grup
        [
            InlineKeyboardButton(
                "⚡ Efek Audio",
                callback_data="help:effects",
                style=eff_style,
            ),
            InlineKeyboardButton(
                "🛡️ Admin Grup",
                callback_data="help:admin",
                style=admin_style,
            ),
        ],
        # Baris 3: Sudo & Info
        [
            InlineKeyboardButton(
                "👑 Sudo & Owner",
                callback_data="help:sudo",
                style=sudo_style,
            ),
            InlineKeyboardButton(
                "ℹ️ Info Sistem",
                callback_data="help:info",
                style=info_style,
            ),
        ],
        # Baris 4: Navigasi Kembali & Tutup
        [
            InlineKeyboardButton(
                back_label,
                callback_data=back_cb,
                style=ButtonStyle.PRIMARY,
            ),
            InlineKeyboardButton(
                "🗑 Tutup Menu",
                callback_data="help:close",
                style=ButtonStyle.DANGER,
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
