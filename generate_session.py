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
import sys

# Coba import Kurigram / Pyrogram
try:
    from kurigram import Client
except ImportError:
    try:
        from pyrogram import Client
    except ImportError:
        print("❌ Error: Library Kurigram / Pyrogram belum terpasang.")
        print("Silakan jalankan: pip install kurigram py-tgcalls")
        sys.exit(1)

from dotenv import load_dotenv

load_dotenv()

BANNER = r"""
=============================================================
   _  __                      __                      ____  __                       
  / |/ /_ _____ ___ ____  ___/ /____ ________ _ ___  / __ \/ /________ ___ ___ _  ___
 /    / // (_-</ _ `/ _ \/ _  / _ `/ __/ _ `/  ( _ ) \__ \/ __/ __/ -_) _ `/  ' \(_-<
/_/|_/\_,_/___/\_,_/_//_/\_,_/\_,_/_/  \_,_/  /___/ /____/\__/_/  \__/\_,_/_/_/_/___/

               🇮🇩 PYROGRAM STRING SESSION GENERATOR 🇮🇩
=============================================================
"""


async def main():
    print(BANNER)
    print("Script ini akan menghasilkan Pyrogram String Session untuk akun asisten bot Anda.\n")

    # Ambil API_ID dan API_HASH dari .env jika ada
    env_api_id = os.getenv("API_ID", "")
    env_api_hash = os.getenv("API_HASH", "")

    if env_api_id and env_api_id != "0":
        use_env = input(f"Gunakan API_ID dari .env ({env_api_id})? (Y/n): ").strip().lower()
        if use_env in ("", "y", "yes"):
            api_id = int(env_api_id)
            api_hash = env_api_hash
        else:
            api_id = int(input("Masukkan API_ID: ").strip())
            api_hash = input("Masukkan API_HASH: ").strip()
    else:
        api_id = int(input("Masukkan API_ID: ").strip())
        api_hash = input("Masukkan API_HASH: ").strip()

    print("\n⏳ Menginisialisasi koneksi ke server Telegram...")

    async with Client(
        name="session_generator",
        api_id=api_id,
        api_hash=api_hash,
        in_memory=True,
    ) as app:
        session_str = await app.export_session_string()
        me = await app.get_me()

        print("\n" + "=" * 60)
        print("🎉 BERHASIL GENERATE STRING SESSION!")
        print("=" * 60)
        print(f"Akun: {me.first_name} (@{me.username or me.id})")
        print("\n👇 Salin kode session string di bawah ini:\n")
        print(session_str)
        print("\n" + "=" * 60)

        # Simpan otomatis ke .env jika user menyetujui
        env_file_path = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_file_path):
            save_env = input("\nSimpan STRING_SESSION otomatis ke file .env? (Y/n): ").strip().lower()
            if save_env in ("", "y", "yes"):
                with open(env_file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                session_updated = False
                new_lines = []
                for line in lines:
                    if line.startswith("STRING_SESSION="):
                        new_lines.append(f"STRING_SESSION={session_str}\n")
                        session_updated = True
                    else:
                        new_lines.append(line)

                if not session_updated:
                    new_lines.append(f"\nSTRING_SESSION={session_str}\n")

                with open(env_file_path, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)

                print("✅ STRING_SESSION berhasil disimpan ke .env!")
                print("Sekarang Anda dapat langsung menjalankan bot dengan: python3 main.py")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n❌ Pembuatan session dibatalkan.")
    except Exception as e:
        print(f"\n❌ Terjadi kesalahan: {e}")
