import json
import os
import secrets
import shlex
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

from . import client


ADDON = xbmcaddon.Addon()
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
PID_FILE = os.path.join(PROFILE, "ersatztv-server.json")
LOG_FILE = os.path.join(PROFILE, "ersatztv-server.log")


def ensure_management_key(regenerate=False):
    key = client.setting("management_key")
    if key and not regenerate:
        return key
    key = secrets.token_urlsafe(32)
    ADDON.setSetting("management_key", key)
    client.log("Generated a Kodi management API key for the local ErsatzTV server")
    return key


def generate_management_key():
    existing = client.setting("management_key")
    if existing and not xbmcgui.Dialog().yesno(
            "Kodi management API key",
            "Replace the existing management key? The local ErsatzTV server must be restarted afterward."):
        return
    ensure_management_key(True)
    xbmcgui.Dialog().ok(
        "Kodi management API key",
        "A secure key was generated and saved. Kodi will pass it to a locally started ErsatzTV server automatically.")


def _ensure_profile():
    if not xbmcvfs.exists(PROFILE):
        xbmcvfs.mkdirs(PROFILE)


def _pid_record():
    try:
        with open(PID_FILE, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def _alive(pid):
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError):
        return False


def reachable(timeout=1.5):
    url = client.setting("server_url", "http://localhost:8409").rstrip("/") + "/"
    try:
        with urllib.request.urlopen(url, timeout=timeout):
            return True
    except (urllib.error.URLError, OSError):
        return False


def state():
    record = _pid_record()
    running = _alive(record.get("pid"))
    if not running and record:
        try:
            os.remove(PID_FILE)
        except OSError:
            pass
    return {"running": running, "reachable": reachable(), "pid": record.get("pid") if running else None}


def choose_executable():
    current = client.setting("server_executable")
    selected = xbmcgui.Dialog().browseSingle(1, "Select the ErsatzTV executable", "files", defaultt=current)
    if selected:
        ADDON.setSetting("server_executable", selected)
        xbmcgui.Dialog().notification("ErsatzTV", "Server executable saved", xbmcgui.NOTIFICATION_INFO, 3000)


def start(interactive=True):
    current = state()
    if current["running"]:
        if interactive:
            xbmcgui.Dialog().ok("Server Configuration", "The server process started by Kodi is already running.")
        return True
    executable = xbmcvfs.translatePath(client.setting("server_executable")).strip()
    if not executable:
        if interactive:
            xbmcgui.Dialog().ok("Server Configuration", "Choose the ErsatzTV executable in Settings first.")
        return False
    if not os.path.isfile(executable):
        if interactive:
            xbmcgui.Dialog().ok("Server Configuration", "The configured executable was not found:\n\n{}".format(executable))
        return False
    arguments = shlex.split(client.setting("server_arguments"), posix=sys.platform != "win32")
    command = [executable] + arguments
    working_dir = xbmcvfs.translatePath(client.setting("server_working_directory")).strip() or os.path.dirname(executable)
    _ensure_profile()
    environment = os.environ.copy()
    environment["ETV_KODI_MANAGEMENT_KEY"] = ensure_management_key()
    options = {"cwd": working_dir, "stdin": subprocess.DEVNULL, "env": environment}
    if sys.platform == "win32":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    else:
        options["start_new_session"] = True
    try:
        with open(LOG_FILE, "ab", buffering=0) as log_handle:
            process = subprocess.Popen(command, stdout=log_handle, stderr=subprocess.STDOUT, **options)
        with open(PID_FILE, "w", encoding="utf-8") as handle:
            json.dump({"pid": process.pid, "executable": executable, "started": time.time()}, handle)
    except (OSError, ValueError) as exc:
        client.log("Unable to start local server: {}".format(exc), xbmc.LOGERROR)
        if interactive:
            xbmcgui.Dialog().ok("Server Configuration", "Could not start ErsatzTV.\n\n{}".format(exc))
        return False
    timeout = max(1, int(client.setting("server_start_timeout", "30")))
    progress = xbmcgui.DialogProgress()
    if interactive:
        progress.create("Server Configuration", "Waiting for ErsatzTV to become available…")
    ready = False
    for elapsed in range(timeout):
        if reachable():
            ready = True
            break
        if not _alive(process.pid):
            break
        if interactive:
            progress.update(int((elapsed + 1) * 100 / timeout))
            if progress.iscanceled():
                break
        xbmc.sleep(1000)
    if interactive:
        progress.close()
        message = "ErsatzTV is running and reachable." if ready else "The process started, but the server URL is not reachable yet. Check the URL and server log."
        xbmcgui.Dialog().ok("Server Configuration", message)
    return ready


def stop(interactive=True):
    record = _pid_record()
    pid = record.get("pid")
    if not _alive(pid):
        if interactive:
            xbmcgui.Dialog().ok("Server Configuration", "Kodi does not have a running local server process to stop.")
        return True
    try:
        os.kill(int(pid), signal.SIGTERM)
        for _ in range(10):
            if not _alive(pid):
                break
            xbmc.sleep(500)
        stopped = not _alive(pid)
    except OSError as exc:
        stopped = False
        client.log("Unable to stop local server: {}".format(exc), xbmc.LOGERROR)
    if stopped:
        try:
            os.remove(PID_FILE)
        except OSError:
            pass
    if interactive:
        xbmcgui.Dialog().ok("Server Configuration", "ErsatzTV stopped." if stopped else "ErsatzTV did not stop. Close it from the operating system.")
    return stopped


def restart():
    if stop(False):
        start(True)


def show_status():
    current = state()
    process_text = "Running (PID {})".format(current["pid"]) if current["running"] else "Not running"
    network_text = "Reachable" if current["reachable"] else "Not reachable"
    xbmcgui.Dialog().ok("Server Configuration", "Kodi-started process: {}\nServer URL: {}\nConnection: {}".format(
        process_text, client.setting("server_url", "http://localhost:8409"), network_text))


def show_log():
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as handle:
            content = handle.read()[-12000:]
    except OSError:
        content = "No local server log exists yet."
    xbmcgui.Dialog().textviewer("ErsatzTV server log", content)


def home():
    from .router import HANDLE, finish, item, url
    current = state()
    xbmcplugin.setPluginCategory(HANDLE, "Server Configuration")
    status = "Running" if current["running"] else "Stopped"
    connection = "reachable" if current["reachable"] else "not reachable"
    item("Status: {} · {}".format(status, connection), url("server_status"))
    item("Test server connection", url("test"))
    item("Choose ErsatzTV executable", url("server_choose"))
    item("Generate management API key", url("server_generate_key"))
    item("Start server", url("server_start"))
    item("Stop server", url("server_stop"))
    item("Restart server", url("server_restart"))
    item("View server log", url("server_log"))
    item("Server settings", url("settings"))
    finish(cache=False)


def autostart():
    if client.setting_bool("server_autostart") and not state()["reachable"]:
        start(False)
