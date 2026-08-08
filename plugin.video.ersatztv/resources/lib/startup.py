import os
import time

import xbmc
import xbmcgui
import xbmcvfs

from . import client, pvr, server


TITLE = "ErsatzTV"


def _notify(message, error=False):
    client.log(message, xbmc.LOGERROR if error else xbmc.LOGINFO)
    if client.setting_bool("startup_notifications", True):
        xbmcgui.Dialog().notification(
            TITLE, message,
            xbmcgui.NOTIFICATION_ERROR if error else xbmcgui.NOTIFICATION_INFO,
            5000)


def _wait_for_server(monitor, pid):
    timeout = max(5, int(client.setting("server_start_timeout", "30")))
    deadline = time.time() + timeout
    while time.time() < deadline and not monitor.abortRequested():
        if server.reachable(0.25):
            return True
        if pid and not server._alive(pid):
            return False
        if monitor.waitForAbort(0.25):
            return False
    return False


def _wait_for_live_tv(monitor):
    timeout = max(60, int(client.setting("server_start_timeout", "30")) * 4)
    deadline = time.time() + timeout
    channels_announced = False
    epg_announced = False
    while time.time() < deadline and not monitor.abortRequested():
        status = pvr.readiness()
        if status["channels"] and not channels_announced:
            _notify("Channels loaded: {} available".format(status["channels"]))
            channels_announced = True
            if monitor.waitForAbort(2):
                return False
            continue
        if status["epg"] and not epg_announced:
            _notify("Programme guide loaded")
            epg_announced = True
            if monitor.waitForAbort(2):
                return False
            continue
        if status["playable"]:
            _notify("Live TV is now ready.")
            return True
        if monitor.waitForAbort(2):
            return False
    if not monitor.abortRequested():
        missing = "channels and guide data" if not channels_announced else "programme guide data"
        _notify("Live TV is still loading {}. Open PVR Configuration to check setup.".format(missing), True)
    return False


def run():
    monitor = xbmc.Monitor()
    if monitor.waitForAbort(2) or not client.setting_bool("server_autostart", True):
        return

    current = server.state()
    if current["reachable"]:
        _notify("ErsatzTV server is ready")
    else:
        executable = xbmcvfs.translatePath(client.setting("server_executable")).strip()
        if not executable or not os.path.isfile(executable):
            _notify("Setup required: choose the ErsatzTV executable in Server Configuration", True)
            return
        _notify("ErsatzTV server is starting")
        if not current["running"]:
            if not server.start(False):
                _notify("ErsatzTV server could not be started. Check Server Configuration.", True)
                return
            current = server.state()
        if not _wait_for_server(monitor, current["pid"]):
            _notify("ErsatzTV server did not become ready. Check the server log.", True)
            return
        _notify("ErsatzTV server is ready")

    setup = pvr.configure_automatic(monitor, _notify)
    if not setup["ok"]:
        _notify(setup["message"], True)
        return
    if setup["changed"]:
        _notify("IPTV Simple Client configured")
        if monitor.waitForAbort(2):
            return
    _wait_for_live_tv(monitor)
