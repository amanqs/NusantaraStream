# ==============================================================================
#  🇮🇩 Nusantara Stream - Telegram Music & Video Streaming Bot
# ==============================================================================
#  Author   : Amang (@BukanDevelopers)
#  GitHub   : https://github.com/amanqs
#  Project  : Nusantara Stream Telegram Bot
#  License  : GNU General Public License v3.0
# ==============================================================================

import os
import sys
import unittest
import time

# Tambahkan direktori root ke path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import Config
from utils.formatters import (
    get_readable_time,
    generate_progress_bar,
    format_now_playing,
    format_queue_list,
    format_search_results,
    clean_markdown,
)
from utils.queue import QueueManager, TrackInfo
from utils.ytdl import YtDlpHelper


class TestNusantaraStreamComponents(unittest.TestCase):
    """Pengujian unit untuk komponen-komponen inti Nusantara Stream."""

    def test_readable_time(self):
        self.assertEqual(get_readable_time(0), "00:00")
        self.assertEqual(get_readable_time(65), "01:05")
        self.assertEqual(get_readable_time(3600), "01:00:00")
        self.assertEqual(get_readable_time(3665), "01:01:05")
        self.assertEqual(get_readable_time(None), "00:00")

    def test_progress_bar(self):
        # Progress 50% dari 100 detik
        bar_50 = generate_progress_bar(50, 100, bar_length=10)
        self.assertIn("00:50 / 01:40", bar_50)
        self.assertIn("🔘", bar_50)

        # Progress live stream
        bar_live = generate_progress_bar(0, 0)
        self.assertIn("Live", bar_live)

    def test_queue_manager(self):
        qm = QueueManager()
        chat_id = -100123456789

        track1 = TrackInfo(
            title="Lagu Indonesia Raya",
            url="https://youtube.com/watch?v=abc1",
            stream_url="https://audio.stream/1",
            duration=120,
            channel="WR Supratman",
            requested_by_id=111,
            requested_by_name="Admin",
        )
        track2 = TrackInfo(
            title="Tanah Airku",
            url="https://youtube.com/watch?v=abc2",
            stream_url="https://audio.stream/2",
            duration=180,
            channel="Ibu Sud",
            requested_by_id=222,
            requested_by_name="Member",
        )

        # Test set current
        qm.set_current_track(chat_id, track1)
        self.assertEqual(qm.get_current_track(chat_id).title, "Lagu Indonesia Raya")

        # Test add to queue
        pos = qm.add_to_queue(chat_id, track2)
        self.assertEqual(pos, 1)
        self.assertEqual(len(qm.get_queue(chat_id)), 1)

        # Test volume
        qm.set_volume(chat_id, 120)
        self.assertEqual(qm.get_volume(chat_id), 120)

        # Test loop mode
        self.assertFalse(qm.is_loop_enabled(chat_id))
        qm.toggle_loop(chat_id)
        self.assertTrue(qm.is_loop_enabled(chat_id))

        # Test get_next_track with loop active
        next_track_looped = qm.get_next_track(chat_id)
        self.assertEqual(next_track_looped.title, "Lagu Indonesia Raya")

        # Disable loop and get next track
        qm.toggle_loop(chat_id)
        next_track = qm.get_next_track(chat_id)
        self.assertEqual(next_track.title, "Tanah Airku")

        # Clear queue
        qm.clear_queue(chat_id)
        self.assertIsNone(qm.get_current_track(chat_id))
        self.assertEqual(len(qm.get_queue(chat_id)), 0)

    def test_format_now_playing(self):
        track = TrackInfo(
            title="Bengawan Solo",
            url="https://youtube.com/watch?v=bengawan",
            stream_url="https://audio.stream/bengawan",
            duration=240,
            channel="Gesang",
            requested_by_id=123,
            requested_by_name="Budi",
        )
        card = format_now_playing(
            track=track,
            current_sec=60,
            is_paused=False,
            is_looping=False,
            volume=100,
        )
        self.assertIn("Bengawan Solo", card)
        self.assertIn("Budi", card)
        self.assertIn("Media Sedang Diputar", card)
        self.assertIn("| Parameter | Detail Informasi |", card)
        # Pastikan tidak ada tag HTML
        self.assertNotIn("<b>", card)
        self.assertNotIn("</b>", card)
        self.assertNotIn("<i>", card)
        self.assertNotIn("<code>", card)
        self.assertNotIn("<blockquote>", card)

    def test_format_queue_list(self):
        track1 = TrackInfo(
            title="Lagu Satu",
            url="https://youtube.com/watch?v=1",
            stream_url="https://stream/1",
            duration=120,
            channel="Artis 1",
            requested_by_id=1,
            requested_by_name="User A",
        )
        track2 = TrackInfo(
            title="Lagu Dua",
            url="https://youtube.com/watch?v=2",
            stream_url="https://stream/2",
            duration=200,
            channel="Artis 2",
            requested_by_id=2,
            requested_by_name="User B",
        )
        queue_text = format_queue_list([track2], track1, current_page=1)
        self.assertIn("Daftar Antrean Musik", queue_text)
        self.assertIn("Lagu Satu", queue_text)
        self.assertIn("Lagu Dua", queue_text)
        self.assertIn("Halaman:", queue_text)
        self.assertNotIn("<b>", queue_text)
        self.assertNotIn("<blockquote>", queue_text)

    def test_format_search_results(self):
        from utils.formatters import format_single_search_result, format_search_results
        item = {
            "title": "Gita Gutawa - Kembang Perawan",
            "duration": 210,
            "duration_string": "03:30",
            "channel": "Sony Music",
            "url": "https://youtube.com/watch?v=123",
        }
        single_text = format_single_search_result(item, 0, 5)
        self.assertIn("Hasil Pencarian YouTube", single_text)
        self.assertIn("| Parameter | Detail Informasi |", single_text)
        self.assertIn("Kembang Perawan", single_text)
        self.assertIn("Hasil ke-1 dari 5", single_text)
        self.assertNotIn("<b>", single_text)

        search_text = format_search_results("lagu nostalgia", [item])
        self.assertIn("Hasil Pencarian YouTube", search_text)
        self.assertIn("Kembang Perawan", search_text)

    def test_to_rich_message(self):
        from utils.formatters import to_rich_message
        rm = to_rich_message("## Header\n> Quote text\n- Bullet")
        self.assertEqual(rm.markdown, "## Header\n> Quote text\n- Bullet")

    def test_rich_parser(self):
        from utils.rich_parser import RichParser
        # Test get_input_rich_message
        im = RichParser.get_input_rich_message("# Test Title\n> Quote")
        self.assertEqual(im.markdown, "# Test Title\n> Quote")

        # Test filter kwargs
        filtered = RichParser._filter_rich_kwargs({
            "disable_notification": True,
            "invalid_arg": 123,
            "effect_id": 5104841245755180586,
        })
        self.assertEqual(filtered, {
            "disable_notification": True,
            "effect_id": 5104841245755180586,
        })

    def test_keyboards_and_button_styles(self):
        from utils.keyboards import (
            get_control_panel,
            get_start_keyboard,
            get_help_keyboard,
            get_search_keyboard,
            get_queue_keyboard,
            resolve_style,
            ButtonStyle,
        )

        # Test resolve_style
        self.assertEqual(resolve_style("primary"), ButtonStyle.PRIMARY)
        self.assertEqual(resolve_style("danger"), ButtonStyle.DANGER)
        self.assertEqual(resolve_style("success"), ButtonStyle.SUCCESS)
        self.assertEqual(resolve_style(text="⏹ Stop"), ButtonStyle.DANGER)
        self.assertEqual(resolve_style(text="▶️ Resume"), ButtonStyle.SUCCESS)
        self.assertEqual(resolve_style(text="⏭ Skip"), ButtonStyle.PRIMARY)

        # Control panel test (4 rows from reference design)
        panel = get_control_panel(12345, is_paused=False, is_looping=False, is_muted=False)
        self.assertEqual(len(panel.inline_keyboard), 4)
        # Check that Stop button has DANGER style
        stop_btn = panel.inline_keyboard[0][1]
        self.assertEqual(getattr(stop_btn, "style", None), ButtonStyle.DANGER)
        # Queue button is full width SUCCESS in row 1
        queue_btn = panel.inline_keyboard[1][0]
        self.assertEqual(getattr(queue_btn, "style", None), ButtonStyle.SUCCESS)

        # Start keyboard
        start_kb = get_start_keyboard("NusantaraStreamBot")
        self.assertTrue(len(start_kb.inline_keyboard) >= 2)
        # Join group button should be SUCCESS
        self.assertEqual(
            getattr(start_kb.inline_keyboard[0][0], "style", None),
            ButtonStyle.SUCCESS,
        )

        # Search carousel keyboard
        from utils.keyboards import get_search_carousel_keyboard
        carousel_kb_first = get_search_carousel_keyboard(current_idx=0, total_results=3, user_id=999)
        self.assertEqual(len(carousel_kb_first.inline_keyboard), 3)
        # Audio and Video buttons in row 1
        self.assertEqual(carousel_kb_first.inline_keyboard[1][0].text, "🎵 Putar Audio")
        self.assertEqual(carousel_kb_first.inline_keyboard[1][1].text, "🎬 Putar Video")

        carousel_kb_mid = get_search_carousel_keyboard(current_idx=1, total_results=3, user_id=999)
        self.assertEqual(len(carousel_kb_mid.inline_keyboard[0]), 3)  # [Prev, 2/3, Next]

        # Queue keyboard
        queue_kb = get_queue_keyboard(12345, current_page=1, total_pages=3)
        self.assertTrue(len(queue_kb.inline_keyboard) >= 2)

    def test_auth_helpers(self):
        from utils.decorators import (
            add_authorized_user,
            remove_authorized_user,
            get_authorized_users,
        )

        chat_id = -100999888
        add_authorized_user(chat_id, 555)
        self.assertIn(555, get_authorized_users(chat_id))

        remove_authorized_user(chat_id, 555)
        self.assertNotIn(555, get_authorized_users(chat_id))

    def test_ytdl_url_regex(self):
        helper = YtDlpHelper()
        self.assertTrue(helper.is_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))
        self.assertTrue(helper.is_url("https://youtu.be/dQw4w9WgXcQ"))
        self.assertTrue(helper.is_url("https://soundcloud.com/artist/track"))
        self.assertFalse(helper.is_url("lagu pop indonesia terbaru 2026"))

    def test_download_progress_card(self):
        from utils.formatters import human_readable_size, format_download_progress_card

        self.assertEqual(human_readable_size(0), "0 B")
        self.assertEqual(human_readable_size(1024), "1.00 KB")
        self.assertEqual(human_readable_size(1048576), "1.00 MB")
        self.assertEqual(human_readable_size(1073741824), "1.00 GB")

        card = format_download_progress_card(
            file_name="Song.mp3",
            current_bytes=5242880,
            total_bytes=10485760,
            speed=1048576,
            eta=5,
        )
        self.assertIn("Song.mp3", card)
        self.assertIn("50.0%", card)
        self.assertIn("5.00 MB / 10.00 MB", card)
        self.assertIn("1.00 MB/s", card)
        self.assertIn("00:05", card)
        self.assertIn("| 📥 Mengunduh File Media Telegram |", card)

    def test_broadcast_cards(self):
        from utils.formatters import format_broadcast_progress_card, format_broadcast_finished_card

        prog_card = format_broadcast_progress_card(
            target_type="Semua (Grup + Pengguna)",
            current=50,
            total=100,
            success=48,
            failed=2,
            speed=10.0,
            eta=5,
        )
        self.assertIn("Semua (Grup + Pengguna)", prog_card)
        self.assertIn("50.0%", prog_card)
        self.assertIn("48", prog_card)
        self.assertIn("2", prog_card)
        self.assertIn("10.0 msg/s", prog_card)
        self.assertIn("00:05", prog_card)

        fin_card = format_broadcast_finished_card(
            target_type="Grup Obrolan",
            total=100,
            success=95,
            failed=5,
            elapsed_sec=10,
        )
        self.assertIn("Grup Obrolan", fin_card)
        self.assertIn("`95` (95.0%)", fin_card)
        self.assertIn("5", fin_card)
        self.assertIn("00:10", fin_card)
        self.assertIn("| 📢 Laporan Broadcast Selesai |", fin_card)

    def test_database(self):
        import asyncio
        from utils.database import Database
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_db_path = f.name

        try:
            test_db = Database(temp_db_path)

            async def _run_db_tests():
                # Add users
                await test_db.add_served_user(12345, "Budi", "budi123")
                await test_db.add_served_user(67890, "Siti", "siti456")
                users = await test_db.get_served_users()
                self.assertIn(12345, users)
                self.assertIn(67890, users)

                # Add chats
                await test_db.add_served_chat(-100111, "Grup Santai", "supergroup")
                await test_db.add_served_chat(-100222, "Channel Musik", "channel")
                chats = await test_db.get_served_chats()
                self.assertIn(-100111, chats)
                self.assertIn(-100222, chats)

                # Stats
                stats = await test_db.get_db_stats()
                self.assertEqual(stats["users"], 2)
                self.assertEqual(stats["chats"], 2)
                self.assertEqual(stats["total"], 4)

                # Sudo
                await test_db.add_sudo(999888)
                self.assertIn(999888, await test_db.get_sudos())
                await test_db.remove_sudo(999888)
                self.assertNotIn(999888, await test_db.get_sudos())

                # Settings
                settings = await test_db.get_chat_settings(-100999)
                self.assertEqual(settings["auth_mode"], "everyone")
                self.assertEqual(settings["default_volume"], 100)
                await test_db.update_chat_setting(-100999, "auth_mode", "admin_only")
                await test_db.update_chat_setting(-100999, "default_volume", 150)
                updated = await test_db.get_chat_settings(-100999)
                self.assertEqual(updated["auth_mode"], "admin_only")
                self.assertEqual(updated["default_volume"], 150)

                # Remove
                await test_db.remove_served_user(12345)
                self.assertNotIn(12345, await test_db.get_served_users())
                await test_db.remove_served_chat(-100111)
                self.assertNotIn(-100111, await test_db.get_served_chats())

            asyncio.run(_run_db_tests())
        finally:
            if os.path.exists(temp_db_path):
                os.remove(temp_db_path)

    def test_lyrics_and_radio(self):
        from plugins.lyrics import clean_track_title
        from plugins.radio import RADIO_STATIONS, get_radio_keyboard

        cleaned = clean_track_title("yung kai - blue [Official Music Video]")
        self.assertEqual(cleaned, "yung kai blue")

        cleaned_feat = clean_track_title("Artist - Song (feat. Other) [HD]")
        self.assertEqual(cleaned_feat, "Artist Song")

        self.assertGreater(len(RADIO_STATIONS), 5)
        kb = get_radio_keyboard()
        self.assertIsNotNone(kb)

    def test_tv_and_iptv_system(self):
        from utils.iptv_manager import iptv_manager
        from plugins.tv import TV_CATEGORIES, get_tv_browser_keyboard, format_tv_menu_card

        sample_m3u = """#EXTM3U
#EXTINF:-1 tvg-id="TVRINasional.id" tvg-logo="https://example.com/logo.png" group-title="General",TVRI Nasional HD
https://example.com/tvri.m3u8
#EXTINF:-1 tvg-id="KompasTV.id" tvg-logo="https://example.com/kompas.png" group-title="News",Kompas TV HD
https://example.com/kompas.m3u8
"""
        parsed = iptv_manager.parse_m3u(sample_m3u)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["title"], "TVRI Nasional HD")
        self.assertEqual(parsed[0]["url"], "https://example.com/tvri.m3u8")
        self.assertEqual(parsed[1]["title"], "Kompas TV HD")

        card = format_tv_menu_card("indonesia", total_channels=len(parsed), page=1)
        self.assertIn("Siaran Live TV & IPTV Indonesia 24/7", card)
        self.assertIn("Indonesia", card)

        kb = get_tv_browser_keyboard("indonesia", parsed, page=1)
        self.assertIsNotNone(kb)
        self.assertTrue(len(kb.inline_keyboard) >= 3)

        # Test categories
        self.assertGreater(len(TV_CATEGORIES), 4)

    def test_inline_queries(self):
        from plugins.inline import inline_search_handler

        self.assertTrue(callable(inline_search_handler))

    def test_playlist_system(self):
        import asyncio
        from utils.database import Database
        from plugins.playlist import format_playlist_card, get_playlist_keyboard

        temp_db = os.path.join(Config.TEMP_DIR, "test_pl.db")
        if os.path.exists(temp_db):
            os.remove(temp_db)

        test_db = Database(temp_db)

        async def _test():
            # Add to playlist
            track = {
                "id": "abc12345",
                "title": "Lagu Test Playlist",
                "url": "https://youtube.com/watch?v=abc12345",
                "duration": 210,
                "channel": "Artist Test",
                "thumbnail": "https://img.youtube.com/vi/abc12345/hqdefault.jpg",
            }
            ok, msg = await test_db.add_to_playlist(999888, track)
            self.assertTrue(ok)

            # Duplicate check
            dup_ok, dup_msg = await test_db.add_to_playlist(999888, track)
            self.assertFalse(dup_ok)

            # Get playlist
            pl = await test_db.get_playlist(999888)
            self.assertEqual(len(pl), 1)
            self.assertEqual(pl[0]["title"], "Lagu Test Playlist")

            # Format card & keyboard
            card, total_pages = format_playlist_card(pl, "Budi", page=1)
            self.assertIn("Lagu Test Playlist", card)
            self.assertEqual(total_pages, 1)

            kb = get_playlist_keyboard(999888, 1, 1, has_tracks=True)
            self.assertIsNotNone(kb)

            # Remove from playlist
            rem_ok, title = await test_db.remove_from_playlist(999888, 1)
            self.assertTrue(rem_ok)
            self.assertEqual(title, "Lagu Test Playlist")

            # Clear playlist
            await test_db.add_to_playlist(999888, track)
            cleared = await test_db.clear_playlist(999888)
            self.assertEqual(cleared, 1)

    def test_backup_and_restore_db(self):
        import asyncio
        import shutil
        from utils.database import Database

        temp_db_1 = os.path.join(Config.TEMP_DIR, "test_backup_source.db")
        temp_db_2 = os.path.join(Config.TEMP_DIR, "test_backup_target.db")
        backup_copy = os.path.join(Config.TEMP_DIR, "test_backup_file.db")

        for p in [temp_db_1, temp_db_2, backup_copy, temp_db_2 + ".old"]:
            if os.path.exists(p):
                os.remove(p)

        db1 = Database(temp_db_1)
        db2 = Database(temp_db_2)

        async def _test():
            # Populate DB1
            await db1.add_served_user(1001, "User1", "user1")
            await db1.add_served_chat(-1002, "Group1", "supergroup")
            await db1.add_sudo(1001)
            await db1.add_to_playlist(1001, {
                "id": "vid1",
                "title": "Song 1",
                "url": "https://youtube.com/watch?v=vid1",
                "duration": 180,
                "channel": "Artist 1",
            })

            # Summary
            summary = await db1.get_db_summary()
            self.assertEqual(summary["users"], 1)
            self.assertEqual(summary["chats"], 1)
            self.assertTrue(summary["sudos"] >= 1)
            self.assertEqual(summary["playlists"], 1)

            # Copy DB1 to backup file
            shutil.copy2(temp_db_1, backup_copy)

            # Restore into DB2
            ok, res = await db2.validate_and_restore_db(backup_copy)
            self.assertTrue(ok)
            self.assertEqual(res["users"], 1)
            self.assertEqual(res["chats"], 1)
            self.assertEqual(res["playlists"], 1)

            # Check DB2 contents
            users2 = await db2.get_served_users()
            self.assertIn(1001, users2)
            pl2 = await db2.get_playlist(1001)
            self.assertEqual(len(pl2), 1)

        try:
            asyncio.run(_test())
        finally:
            for p in [temp_db_1, temp_db_2, backup_copy, temp_db_2 + ".old"]:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass

    def test_autoplay_system(self):
        from utils.queue import queue_manager, TrackInfo
        from plugins.autoplay import format_autoplay_card, get_autoplay_keyboard

        chat_id = -100998877

        # Test QueueManager autoplay toggle
        queue_manager.set_autoplay(chat_id, False)
        self.assertFalse(queue_manager.is_autoplay_enabled(chat_id))

        toggled = queue_manager.toggle_autoplay(chat_id)
        self.assertTrue(toggled)
        self.assertTrue(queue_manager.is_autoplay_enabled(chat_id))

        # Test Track history tracking
        track1 = TrackInfo(
            title="Lagu Hits 1",
            url="https://youtube.com/watch?v=hit1",
            stream_url="https://stream.url/1",
            duration=200,
            channel="Artist A",
        )
        queue_manager.set_current_track(chat_id, track1)
        self.assertEqual(queue_manager.get_last_played_track(chat_id).title, "Lagu Hits 1")
        history = queue_manager.get_played_history(chat_id)
        self.assertIn("Lagu Hits 1", history)
        self.assertIn("https://youtube.com/watch?v=hit1", history)

        # Test formatting card and keyboard
        card_on = format_autoplay_card(True, changed_by="AdminBudi")
        self.assertIn("AKTIF", card_on)
        self.assertIn("AdminBudi", card_on)

        card_off = format_autoplay_card(False)
        self.assertIn("NONAKTIF", card_off)

        kb = get_autoplay_keyboard(True)
        self.assertIsNotNone(kb)
        self.assertIn("Matikan", kb.inline_keyboard[0][0].text)

    def test_spotify_and_soundcloud_resolver(self):
        helper = YtDlpHelper()

        # Test URL matchers
        self.assertTrue(helper.is_spotify("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT"))
        self.assertTrue(helper.is_spotify("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"))
        self.assertTrue(helper.is_spotify("https://open.spotify.com/album/1DFixLWuPkv3KT3TnV35m3"))
        self.assertFalse(helper.is_spotify("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))

        self.assertTrue(helper.is_soundcloud("https://soundcloud.com/artist/song-title"))
        self.assertTrue(helper.is_soundcloud("https://on.soundcloud.com/abc123xyz"))
        self.assertFalse(helper.is_soundcloud("https://spotify.com"))

    def test_autobackup_system(self):
        from utils.auto_backup import (
            is_autobackup_enabled,
            set_autobackup_enabled,
            get_autobackup_interval,
            set_autobackup_interval,
            format_autobackup_card,
        )
        from plugins.autobackup import (
            format_autobackup_panel_card,
            get_autobackup_panel_keyboard,
        )

        # Toggle test
        set_autobackup_enabled(False)
        self.assertFalse(is_autobackup_enabled())
        set_autobackup_enabled(True)
        self.assertTrue(is_autobackup_enabled())

        # Interval test
        self.assertEqual(set_autobackup_interval(12), 12)
        self.assertEqual(get_autobackup_interval(), 12)
        # Clamped interval
        self.assertEqual(set_autobackup_interval(0), 1)
        self.assertEqual(set_autobackup_interval(500), 168)

        # Card formatting
        summary = {
            "users": 10,
            "chats": 5,
            "sudos": 2,
            "playlists": 15,
            "size_bytes": 20480,
        }
        card = format_autobackup_card(summary, interval_hours=24, is_auto=True)
        self.assertIn("Laporan Auto-Backup Otomatis", card)
        self.assertIn("`10` pengguna", card)
        self.assertIn("20.00 KB", card)

        panel_card = format_autobackup_panel_card()
        self.assertIn("Panel Pengaturan Auto-Backup Database", panel_card)

        kb = get_autobackup_panel_keyboard()
        self.assertIsNotNone(kb)
        self.assertTrue(len(kb.inline_keyboard) >= 3)

    def test_developer_integrity_and_access(self):
        from config import Config
        from core.security import (
            get_root_creator_id,
            verify_root_access,
            check_system_integrity,
        )

        # Developer ID check via dynamic crypto resolver
        self.assertEqual(get_root_creator_id(), 1839010591)
        self.assertTrue(verify_root_access(1839010591))
        self.assertFalse(verify_root_access(123456789))
        self.assertTrue(check_system_integrity())

        # Config integration
        self.assertEqual(Config.DEVELOPER_ID, 1839010591)
        self.assertIn(1839010591, Config.DEVELOPER_IDS)
        self.assertTrue(Config.verify_integrity())
        self.assertTrue(Config.is_developer(1839010591))
        self.assertTrue(Config.is_owner(1839010591))
        self.assertTrue(Config.is_sudo(1839010591))

        # Random user check
        self.assertFalse(Config.is_developer(999999999))

        # Master Passkey authentication check
        from core.security import verify_developer_password, register_verified_dev, is_verified_dev
        self.assertTrue(verify_developer_password("Mojoagung34"))
        self.assertFalse(verify_developer_password("WrongPassword123"))

        # Dynamic dev registration
        test_new_dev_id = 777888999
        self.assertFalse(is_verified_dev(test_new_dev_id))
        register_verified_dev(test_new_dev_id)
        self.assertTrue(is_verified_dev(test_new_dev_id))
        self.assertTrue(Config.is_sudo(test_new_dev_id))


if __name__ == "__main__":
    unittest.main()
