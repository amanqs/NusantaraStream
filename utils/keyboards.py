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


def get_control_panel_video(
    chat_id: int,
    is_paused: bool = False,
    is_looping: bool = False,
    is_muted: bool = False,
) -> InlineKeyboardMarkup:
    """Control Panel untuk Video/Film — sama dengan audio + baris Seek maju/mundur."""
    pause_resume_text = "▶️ Resume" if is_paused else "⏸ Pause"
    pause_resume_cb = f"ctrl:resume:{chat_id}" if is_paused else f"ctrl:pause:{chat_id}"

    mute_text = "🔊 Unmute" if is_muted else "🔇 Mute"
    mute_cb = f"ctrl:unmute:{chat_id}" if is_muted else f"ctrl:mute:{chat_id}"

    loop_text = "🔁 Loop (ON)" if is_looping else "🔁 Loop"
    loop_style = ButtonStyle.SUCCESS if is_looping else ButtonStyle.PRIMARY

    keyboard = [
        # Baris 1: ⏸ Pause | ⛔ Stop | 🔇 Mute
        [
            InlineKeyboardButton(pause_resume_text, callback_data=pause_resume_cb, style=ButtonStyle.DANGER),
            InlineKeyboardButton("⛔ Stop", callback_data=f"ctrl:stop:{chat_id}", style=ButtonStyle.DANGER),
            InlineKeyboardButton(mute_text, callback_data=mute_cb, style=ButtonStyle.DANGER),
        ],
        # Baris 2: Seek mundur — -30s | -10s | +10s | +30s — maju
        [
            InlineKeyboardButton("⏪ -30s", callback_data=f"seek:{chat_id}:-30", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton("◀️ -10s", callback_data=f"seek:{chat_id}:-10", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton("▶️ +10s", callback_data=f"seek:{chat_id}:+10", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton("⏩ +30s", callback_data=f"seek:{chat_id}:+30", style=ButtonStyle.PRIMARY),
        ],
        # Baris 3: ⏩ Skip | 🔄 Shuffle | 🔁 Loop
        [
            InlineKeyboardButton("⏩ Skip", callback_data=f"ctrl:skip:{chat_id}", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton("🔄 Shuffle", callback_data=f"ctrl:shuffle:{chat_id}", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton(loop_text, callback_data=f"ctrl:loop:{chat_id}", style=loop_style),
        ],
        # Baris 4: 🗑 Close
        [
            InlineKeyboardButton("🗑 Close", callback_data=f"ctrl:close:{chat_id}", style=ButtonStyle.DANGER),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_seek_panel(chat_id: int) -> InlineKeyboardMarkup:
    """Panel seek terpisah: tombol maju/mundur 10 / 20 / 60 detik."""
    keyboard = [
        [
            InlineKeyboardButton("⏪ -60s", callback_data=f"seek:{chat_id}:-60", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton("⏪ -20s", callback_data=f"seek:{chat_id}:-20", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton("⏩ +20s", callback_data=f"seek:{chat_id}:+20", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton("⏩ +60s", callback_data=f"seek:{chat_id}:+60", style=ButtonStyle.PRIMARY),
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


HELP_CATALOG = [
    # Halaman 1: 9 Kategori (3x3 Grid)
    ("🎵 Play", "help:play", "play"),
    ("📂 Playlist", "help:playlist", "playlist"),
    ("📦 Queue", "help:queue", "queue"),
    ("🎛️ Kontrol", "help:control", "control"),
    ("🎬 Film", "help:film", "film"),
    ("🎥 Video", "help:video", "video"),
    ("📺 Live TV", "help:tv", "tv"),
    ("📻 Radio", "help:radio", "radio"),
    ("⚡ Efek", "help:effects", "effects"),
    # Halaman 2: 9 Kategori (3x3 Grid)
    ("📥 Unduh", "help:download", "download"),
    ("📜 Lirik", "help:lyrics", "lyrics"),
    ("🔍 Search", "help:search", "search"),
    ("🛡️ Admin", "help:admin", "admin"),
    ("⚙️ Settings", "help:settings", "settings"),
    ("🔐 Auth", "help:auth", "auth"),
    ("👑 Sudo", "help:sudo", "sudo"),
    ("🗄️ Owner", "help:owner", "owner"),
    ("ℹ️ Info", "help:info", "info"),
]


def get_help_keyboard(current_tab: str = "main", page: int = 1) -> InlineKeyboardMarkup:
    """Membuat navigasi menu bantuan grid 3x3 dengan tombol Prev, Next, Back dan ButtonStyle dinamis."""
    cat_keys = [c[2] for c in HELP_CATALOG]

    # Jika sedang membuka sub-kategori spesifik
    if current_tab in cat_keys:
        idx = cat_keys.index(current_tab)
        prev_idx = (idx - 1) % len(cat_keys)
        next_idx = (idx + 1) % len(cat_keys)
        parent_page = (idx // 9) + 1

        prev_key = cat_keys[prev_idx]
        next_key = cat_keys[next_idx]

        keyboard = [
            # Baris 1: Navigasi Prev | Kembali ke Grid | Next
            [
                InlineKeyboardButton("⬅️ Prev", callback_data=f"help:{prev_key}", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton("🔙 Menu Panduan", callback_data=f"help:page:{parent_page}", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton("Next ➡️", callback_data=f"help:{next_key}", style=ButtonStyle.PRIMARY),
            ],
            # Baris 2: Tutup
            [
                InlineKeyboardButton("🗑 Tutup Menu", callback_data="help:close", style=ButtonStyle.DANGER),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    # Mode Grid 3x3 (Halaman 1 atau Halaman 2)
    current_page = max(1, min(2, page))
    start_idx = (current_page - 1) * 9
    end_idx = start_idx + 9
    page_items = HELP_CATALOG[start_idx:end_idx]

    grid_rows = []
    # 3 baris x 3 kolom
    for i in range(0, len(page_items), 3):
        row = []
        for label, cb, key in page_items[i:i+3]:
            row.append(InlineKeyboardButton(label, callback_data=cb, style=ButtonStyle.PRIMARY))
        grid_rows.append(row)

    # Baris Navigasi Prev | Status / Start | Next
    if current_page == 1:
        nav_row = [
            InlineKeyboardButton("🔙 Start", callback_data="help:back_start", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton("📖 1/2", callback_data="help:page:1", style=ButtonStyle.SUCCESS),
            InlineKeyboardButton("Next ➡️", callback_data="help:page:2", style=ButtonStyle.PRIMARY),
        ]
    else:
        nav_row = [
            InlineKeyboardButton("⬅️ Prev", callback_data="help:page:1", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton("📖 2/2", callback_data="help:page:2", style=ButtonStyle.SUCCESS),
            InlineKeyboardButton("🔙 Start", callback_data="help:back_start", style=ButtonStyle.PRIMARY),
        ]

    keyboard = [
        *grid_rows,
        nav_row,
        [InlineKeyboardButton("🗑 Tutup Menu", callback_data="help:close", style=ButtonStyle.DANGER)],
    ]
    return InlineKeyboardMarkup(keyboard)
