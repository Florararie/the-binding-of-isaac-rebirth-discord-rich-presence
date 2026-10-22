import os
import time
import tempfile
from pathlib import Path

import psutil

from dataManager import dataManager
from discordManager import discordManager

GAME_PROCESS = "isaac-ng.exe"
REPENTOGON_LAUNCHER_PROCESS = "REPENTOGONLauncher.exe"
STARTUP_TIMEOUT = 120
POLL_INTERVAL = 2

LOCK_FILE = Path(tempfile.gettempdir()) / "isaac-discord-rich-presence.lock"


def find_process(name):
    name = name.lower()

    for process in psutil.process_iter(["name", "cmdline"]):
        try:
            process_name = (process.info.get("name") or "").lower()
            if process_name == name or (
                len(name) > 15 and process_name == name[:15]
            ):
                return process

            # Names can be limited to ~15 chars in some cases
            for argument in process.info.get("cmdline") or []:
                executable = argument.replace("\\", "/").rsplit("/", 1)[-1].lower()
                if executable == name:
                    return process
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return None


def is_game_running():
    return find_process(GAME_PROCESS) is not None


def is_repentogon_launcher_running():
    return find_process(REPENTOGON_LAUNCHER_PROCESS) is not None


def lock_owner_is_running():
    try:
        pid = int(LOCK_FILE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return False

    if pid == os.getpid():
        return False

    try:
        process = psutil.Process(pid)
        command_line = " ".join(process.cmdline()).lower()
        return process.is_running() and (
            "main.py" in command_line or "main.exe" in command_line
        )
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False


def acquire_instance_lock():
    if lock_owner_is_running():
        return False

    try:
        LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
    except OSError:
        # Read only shouldnt stop us
        pass

    return True


def release_instance_lock():
    try:
        if int(LOCK_FILE.read_text(encoding="utf-8").strip()) == os.getpid():
            LOCK_FILE.unlink()
    except (OSError, ValueError):
        pass


def clear_presence(discord):
    try:
        discord.updatePresence(None)
    except Exception as error:
        print(f"Nie udało się wyczyścić presence: {error}")


def wait_for_game_or_launcher():
    deadline = time.monotonic() + STARTUP_TIMEOUT

    while time.monotonic() < deadline:
        if is_game_running() or is_repentogon_launcher_running():
            return True
        time.sleep(1)

    return False


def main():
    if not acquire_instance_lock():
        print("Mod już działa, kończę działanie")
        return

    discord = discordManager()
    data_manager = dataManager()

    try:
        if not wait_for_game_or_launcher():
            print("Gra nie została uruchomiona w wyznaczonym czasie, kończę działanie")
            return

        # Launcher may stay open and allow the game to be relaunched.
        # Mod should live as long as the launcher.
        # Without launcher, as long as the game is alive.
        repentogon_mode = is_repentogon_launcher_running()
        game_was_running = is_game_running()

        if game_was_running:
            print("Gra została uruchomiona")
        else:
            print("Wykryto launcher REPENTOGON, czekam na uruchomienie gry")

        while True:
            game_running = is_game_running()
            launcher_running = is_repentogon_launcher_running()

            if launcher_running:
                repentogon_mode = True

            if repentogon_mode and not launcher_running:
                print("Launcher REPENTOGON został zamknięty, kończę działanie")
                if game_was_running:
                    clear_presence(discord)
                break

            if game_running:
                if not game_was_running:
                    print("Gra została uruchomiona")
                    game_was_running = True

                game_data = data_manager.getGameData()

                if game_data != discord.game_data:
                    print("Powiadamiam discord")
                    discord.updatePresence(game_data)
            else:
                if game_was_running:
                    print("Gra została zamknięta")
                    clear_presence(discord)
                    game_was_running = False

                # Without REPENTOGON there is nothing left to wait for.
                if not repentogon_mode:
                    print("Gra nie jest uruchomiona, kończę działanie")
                    break

                # launcher is open but the game isn't
                if discord.game_data != "launcher":
                    discord.updatePresenceLauncher()

            time.sleep(POLL_INTERVAL)
    finally:
        clear_presence(discord)
        discord.close()
        release_instance_lock()


if __name__ == "__main__":
    main()
