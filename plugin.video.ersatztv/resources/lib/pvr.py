import json
import math
import time
import urllib.request

import xbmc
import xbmcaddon
import xbmcgui

from . import client


IPTV_SIMPLE_ID = "pvr.iptvsimple"


def _router():
    from . import router
    return router


def _rpc(method, params=None):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        payload["params"] = params
    response = json.loads(xbmc.executeJSONRPC(json.dumps(payload)))
    if response.get("error"):
        error = response["error"]
        raise RuntimeError("Kodi JSON-RPC error {}: {}".format(error.get("code", "?"), error.get("message", "Unknown error")))
    return response.get("result")


def _details():
    try:
        return _rpc("Addons.GetAddonDetails", {
            "addonid": IPTV_SIMPLE_ID,
            "properties": ["name", "version", "enabled"]
        }).get("addon", {})
    except Exception:
        return {}


def _urls():
    return (
        client.endpoint(client.setting("m3u_path", "/iptv/channels.m3u")),
        client.endpoint(client.setting("xmltv_path", "/iptv/xmltv.xml")),
    )


def home():
    r = _router()
    details = _details()
    if not details:
        status = "Not installed"
    else:
        status = "Enabled" if details.get("enabled") else "Installed but disabled"
        if details.get("version"):
            status += " · version {}".format(details["version"])
    r.xbmcplugin.setPluginCategory(r.HANDLE, "PVR Configuration")
    r.item("IPTV Simple status: {}".format(status), r.url("pvr_status"), False)
    r.item("Configure IPTV Simple automatically", r.url("pvr_configure"), False)
    r.item("Test ErsatzTV M3U and XMLTV URLs", r.url("pvr_test"), False)
    r.item("Open IPTV Simple settings", r.url("pvr_settings"), False)
    r.item("Reload IPTV Simple and PVR data", r.url("pvr_reload"), False)
    r.item("Open Kodi PVR & Live TV settings", r.url("pvr_kodi_settings"), False)
    r.finish(cache=False)


def _install():
    if _details():
        return True
    if not xbmcgui.Dialog().yesno(
            "IPTV Simple Client required",
            "Kodi's IPTV Simple Client is not installed. Install it now from the official Kodi repository?"):
        return False
    xbmc.executebuiltin("InstallAddon({})".format(IPTV_SIMPLE_ID), wait=True)
    monitor = xbmc.Monitor()
    for _ in range(15):
        if _details():
            return True
        if monitor.waitForAbort(1):
            break
    xbmcgui.Dialog().ok(
        "Installation not completed",
        "Install IPTV Simple Client from:\n\nAdd-ons > Install from repository > Kodi Add-on repository > PVR clients > IPTV Simple Client\n\nThen run this setup again.")
    return False


def _set_pvr_options():
    settings = {
        "pvrmanager.backendchannelorder": True,
        "pvrmanager.usebackendchannelnumbers": True,
        "pvrmanager.usebackendchannelnumbersalways": True,
        "epg.hidenoinfoavailable": False,
        "epg.pastdaystodisplay": max(1, int(math.ceil(float(client.setting("past_hours", "2")) / 24.0))),
        "epg.futuredaystodisplay": max(1, int(math.ceil(float(client.setting("future_hours", "12")) / 24.0))),
    }
    warnings = []
    for setting_id, value in settings.items():
        try:
            _rpc("Settings.SetSettingValue", {"setting": setting_id, "value": value})
        except Exception as exc:
            client.log("Could not set Kodi PVR option {}: {}".format(setting_id, exc), xbmc.LOGWARNING)
            warnings.append(setting_id)
    return warnings


def configure():
    m3u_url, xmltv_url = _urls()
    if not xbmcgui.Dialog().yesno(
            "Configure Kodi Live TV",
            "This will configure IPTV Simple Client for ErsatzTV and enable Kodi channel numbers and guide data.\n\nM3U: {}\n\nXMLTV: {}\n\nContinue?".format(m3u_url, xmltv_url)):
        return
    if not _install():
        return

    addon = xbmcaddon.Addon(IPTV_SIMPLE_ID)
    current_m3u = addon.getSetting("m3uUrl")
    current_epg = addon.getSetting("epgUrl")
    different = ((current_m3u and current_m3u != m3u_url) or (current_epg and current_epg != xmltv_url))
    if different and not xbmcgui.Dialog().yesno(
            "Replace IPTV Simple configuration?",
            "IPTV Simple already contains different playlist or guide URLs. Replace its default configuration with ErsatzTV?"):
        return

    values = {
        "m3uPathType": "1",
        "m3uUrl": m3u_url,
        "m3uCache": "true",
        "epgPathType": "1",
        "epgUrl": xmltv_url,
        "epgCache": "true",
        "epgIgnoreCaseForChannelIds": "true",
        "defaultProviderName": "ErsatzTV",
        "numberByOrder": "false",
    }
    for key, value in values.items():
        if not addon.setSetting(key, value):
            raise RuntimeError("Kodi rejected IPTV Simple setting '{}'".format(key))

    _rpc("Addons.SetAddonEnabled", {"addonid": IPTV_SIMPLE_ID, "enabled": True})
    warnings = _set_pvr_options()
    reload_client(confirm=False)
    message = "IPTV Simple is configured for ErsatzTV. Open TV from Kodi's main menu to view the channels and guide."
    if warnings:
        message += "\n\nSome Kodi PVR preferences could not be changed automatically. The playlist and guide were still configured."
    message += "\n\nIf channels do not appear immediately, restart Kodi once."
    xbmcgui.Dialog().ok("Kodi Live TV configured", message)


def test_urls():
    results = []
    for label, url in zip(("M3U playlist", "XMLTV guide"), _urls()):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Kodi-ErsatzTV/2.3"})
            with urllib.request.urlopen(request, timeout=int(client.setting("timeout", "15"))) as response:
                sample = response.read(512)
                results.append("{}: OK (HTTP {}, data received)".format(label, response.getcode()))
                if not sample:
                    results[-1] = "{}: Connected, but the response was empty".format(label)
        except Exception as exc:
            results.append("{}: FAILED — {}".format(label, exc))
    xbmcgui.Dialog().ok("ErsatzTV PVR connection test", "\n\n".join(results))


def show_status():
    details = _details()
    m3u_url, xmltv_url = _urls()
    if not details:
        state = "IPTV Simple Client is not installed."
    else:
        state = "IPTV Simple Client {} is {}.".format(
            details.get("version", ""), "enabled" if details.get("enabled") else "disabled")
    xbmcgui.Dialog().textviewer(
        "Kodi Live TV status",
        "{}\n\nErsatzTV M3U URL:\n{}\n\nErsatzTV XMLTV URL:\n{}".format(state, m3u_url, xmltv_url))


def open_settings():
    if _install():
        xbmcaddon.Addon(IPTV_SIMPLE_ID).openSettings()


def open_kodi_settings():
    xbmc.executebuiltin("ActivateWindow(Settings)")
    xbmcgui.Dialog().notification("ErsatzTV", "Choose PVR & Live TV", xbmcgui.NOTIFICATION_INFO, 4000)


def reload_client(confirm=True):
    if not _details():
        xbmcgui.Dialog().ok("IPTV Simple Client", "IPTV Simple Client is not installed.")
        return
    if confirm and not xbmcgui.Dialog().yesno(
            "Reload IPTV Simple", "Temporarily disable and re-enable IPTV Simple to reload its playlist and guide?"):
        return
    _rpc("Addons.SetAddonEnabled", {"addonid": IPTV_SIMPLE_ID, "enabled": False})
    time.sleep(0.5)
    _rpc("Addons.SetAddonEnabled", {"addonid": IPTV_SIMPLE_ID, "enabled": True})
    if confirm:
        xbmcgui.Dialog().notification("ErsatzTV", "IPTV Simple reloaded", xbmcgui.NOTIFICATION_INFO, 4000)
