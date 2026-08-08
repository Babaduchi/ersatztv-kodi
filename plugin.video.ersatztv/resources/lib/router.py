import sys
import urllib.parse
from collections import defaultdict
from datetime import datetime

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from . import client
from .model import ChannelGuide


ADDON = xbmcaddon.Addon()
BASE = sys.argv[0]
HANDLE = int(sys.argv[1])

_ENGLISH = {
    32200: "ErsatzTV",
    32201: "Channels",
    32202: "Favourites",
    32203: "Channel groups",
    32204: "On now",
    32205: "Refresh Guide",
    32206: "Test server connection",
    32207: "Settings",
    32208: "Next",
    32209: "Add to favourites",
    32210: "Remove from favourites",
    32211: "View programme guide",
    32212: "No favourite channels. Use a channel's context menu to add one.",
    32213: "No channels match this view.",
    32214: "No channel groups were found in the playlist.",
    32215: "This channel is no longer available.",
    32216: "{} — Programme guide",
    32217: "Now",
    32218: "No programmes are available in the configured guide window.",
    32220: "Loaded {} channels and {} programmes",
    32221: "Refresh failed:\n{}",
    32222: "ErsatzTV connection",
    32223: "Connection successful.\n\nChannels: {}\nProgrammes in configured window: {}",
    32224: "Could not load ErsatzTV data.\n\n{}",
    32225: "Unable to load data. Check the add-on settings and Kodi log.\n\n{}",
    32226: "InputStream Adaptive is enabled in the add-on settings but is not installed. Install it from Kodi's VideoPlayer InputStream add-ons, or disable this option.",
}


def L(string_id):
    translated = ADDON.getLocalizedString(string_id)
    return translated or _ENGLISH.get(string_id, "ErsatzTV")


def url(action, **kwargs):
    query = {"action": action}
    query.update({key: str(value) for key, value in kwargs.items()})
    return BASE + "?" + urllib.parse.urlencode(query)


def item(label, path, folder=False, art=None, info=None, context=None, playable=False):
    li = xbmcgui.ListItem(label=label)
    if art:
        li.setArt(art)
    if info:
        tag = li.getVideoInfoTag()
        tag.setTitle(info.get("title", label))
        tag.setPlot(info.get("plot", ""))
        if info.get("genres"):
            tag.setGenres(info["genres"])
        if info.get("date"):
            tag.setDateAdded(info["date"])
    if playable:
        li.setProperty("IsPlayable", "true")
    if context:
        li.addContextMenuItems(context)
    xbmcplugin.addDirectoryItem(HANDLE, path, li, isFolder=folder)


def finish(content="videos", cache=True):
    xbmcplugin.setContent(HANDLE, content)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=cache)


def empty(label):
    li = xbmcgui.ListItem(label=label)
    li.setProperty("IsPlayable", "false")
    xbmcplugin.addDirectoryItem(HANDLE, "", li, isFolder=False)


def assemble(channels, programmes):
    by_id = defaultdict(list)
    for programme in programmes:
        by_id[programme.channel_id].append(programme)
    now = datetime.now().astimezone()
    result = []
    for channel in channels:
        entries = sorted(by_id[channel.id], key=lambda p: p.start)
        current = next((p for p in entries if p.start <= now < p.stop), None)
        upcoming = next((p for p in entries if p.start > now), None)
        result.append(ChannelGuide(channel, current, upcoming, entries))
    return result


def load_guides(force=False):
    channels, programmes = client.load(force)
    hidden = {x.strip().casefold() for x in client.setting("hide_groups").split(",") if x.strip()}
    channels = [c for c in channels if c.group.casefold() not in hidden]
    guides = assemble(channels, programmes)
    if not client.setting_bool("show_empty_channels", True):
        guides = [guide for guide in guides if guide.programmes]
    mode = client.setting("sort_mode", "number")
    if mode == "name":
        guides.sort(key=lambda x: x.channel.name.casefold())
    else:
        def key(guide):
            try:
                return (0, float(guide.channel.number), guide.channel.name.casefold())
            except ValueError:
                return (1, 0, guide.channel.name.casefold())
        guides.sort(key=key)
    return guides


def home():
    if client.setting_bool("server_autostart"):
        from . import server
        server.autostart()
    layout = client.setting("home_layout", "sections")
    if layout == "channels":
        return channels()
    if layout == "favorites":
        return channels(favorites_only=True)
    xbmcplugin.setPluginCategory(HANDLE, L(32200))
    item(L(32201), url("channels"), True)
    item(L(32202), url("favorites"), True)
    item(L(32203), url("groups"), True)
    item(L(32204), url("now"), True)
    item(L(32205), url("refresh"), False)
    item("Server Configuration", url("server"), True)
    item("PVR Configuration", url("pvr"), True)
    if client.setting_bool("show_management", True):
        item("Channel & Schedule Configuration", url("manage"), True)
    item(L(32207), url("settings"), False)
    finish(cache=False)


def channel_label(guide):
    channel = guide.channel
    bits = []
    if client.setting_bool("channel_numbers", True) and channel.number:
        bits.append(channel.number)
    bits.append(channel.name)
    if client.setting_bool("show_group") and channel.group:
        bits.append("[{}]".format(channel.group))
    label = " · ".join(bits)
    if guide.now:
        label += "  —  " + guide.now.title
        if client.setting_bool("show_next", True) and guide.next:
            label += "  |  {}: ".format(L(32208)) + guide.next.title
    return label


def artwork(guide, programme=None):
    mode = client.setting("artwork_mode", "programme")
    if mode == "none":
        return {}
    image = guide.channel.logo
    if mode == "programme" and programme and programme.icon:
        image = programme.icon
    if not image:
        return {}
    return {"thumb": image, "icon": image, "poster": image, "fanart": image}


def channels(group=None, favorites_only=False, now_only=False):
    guides = load_guides()
    favs = client.favourites()
    heading = group or (L(32202) if favorites_only else L(32204) if now_only else L(32201))
    xbmcplugin.setPluginCategory(HANDLE, heading)
    count = 0
    for guide in guides:
        channel = guide.channel
        if group is not None and channel.group != group:
            continue
        if favorites_only and channel.id not in favs:
            continue
        if now_only and not guide.now:
            continue
        count += 1
        current = guide.now
        plot = current.description if current and client.setting_bool("programme_plot", True) else ""
        if current:
            plot = "{} – {}\n{}".format(format_time(current.start), format_time(current.stop), plot).strip()
        action = "unfavorite" if channel.id in favs else "favorite"
        context = [
            (L(32210) if action == "unfavorite" else L(32209), "RunPlugin({})".format(url(action, id=channel.id))),
            (L(32211), "Container.Update({})".format(url("guide", id=channel.id))),
        ]
        item(channel_label(guide), url("play", stream=channel.url, name=channel.name, logo=channel.logo),
             art=artwork(guide, current), info={"title": current.title if current else channel.name, "plot": plot,
             "genres": current.category if current else []}, context=context, playable=True)
    if count == 0:
        empty(L(32212) if favorites_only else L(32213))
    finish("videos", cache=False)


def groups():
    xbmcplugin.setPluginCategory(HANDLE, L(32203))
    values = sorted({g.channel.group for g in load_guides() if g.channel.group}, key=str.casefold)
    for group in values:
        item(group, url("channels", group=group), True)
    if not values:
        empty(L(32214))
    finish(cache=False)


def guide(channel_id):
    selected = next((g for g in load_guides() if g.channel.id == channel_id), None)
    if not selected:
        empty(L(32215))
        return finish(cache=False)
    xbmcplugin.setPluginCategory(HANDLE, L(32216).format(selected.channel.name))
    now = datetime.now().astimezone()
    for programme in selected.programmes:
        marker = L(32217) + " · " if programme.start <= now < programme.stop else ""
        label = "{}{}–{}  {}".format(marker, format_time(programme.start), format_time(programme.stop), programme.title)
        if programme.subtitle:
            label += " — " + programme.subtitle
        plot = programme.description if client.setting_bool("programme_plot", True) else ""
        item(label, url("play", stream=selected.channel.url, name=selected.channel.name, logo=selected.channel.logo),
             art=artwork(selected, programme), info={"title": programme.title, "plot": plot, "genres": programme.category,
             "date": programme.start.strftime("%Y-%m-%d %H:%M:%S")}, playable=True)
    if not selected.programmes:
        empty(L(32218))
    finish("episodes", cache=False)


def format_time(value):
    mode = client.setting("time_format", "system")
    if mode == "12":
        return value.strftime("%I:%M %p").lstrip("0")
    if mode == "24":
        return value.strftime("%H:%M")
    system_format = xbmc.getRegion("time").lower()
    if "%p" in system_format or "xx" in system_format or "am/pm" in system_format:
        return value.strftime("%I:%M %p").lstrip("0")
    return value.strftime("%H:%M")


def play(stream, name, logo):
    stream = client.endpoint(stream)
    if client.setting_bool("server_autostart"):
        server_url = client.setting("server_url", "http://localhost:8409")
        if urllib.parse.urlsplit(stream).netloc == urllib.parse.urlsplit(server_url).netloc:
            from . import server
            current = server.state()
            if current["running"] and not current["reachable"]:
                if not server.wait_until_ready(current["pid"], True, False):
                    xbmcgui.Dialog().ok("ErsatzTV", "The local server is still unavailable. Check Server Configuration and the server log.")
                    xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
                    return
    li = xbmcgui.ListItem(label=name, path=stream)
    li.setArt({"thumb": logo, "icon": logo})
    mime = client.setting("mime_type", "auto")
    if mime != "auto":
        li.setMimeType(mime)
    elif ".m3u8" in urllib.parse.urlsplit(stream).path.lower():
        li.setMimeType("application/vnd.apple.mpegurl")
    if client.setting_bool("inputstream_adaptive") and (mime == "application/vnd.apple.mpegurl" or ".m3u8" in stream.lower()):
        if not xbmc.getCondVisibility("System.HasAddon(inputstream.adaptive)"):
            xbmcgui.Dialog().ok("ErsatzTV", L(32226))
            xbmcplugin.setResolvedUrl(HANDLE, False, li)
            return
        li.setProperty("inputstream", "inputstream.adaptive")
        li.setProperty("inputstream.adaptive.manifest_type", "hls")
    xbmcplugin.setResolvedUrl(HANDLE, True, li)


def refresh():
    client.clear_cache()
    try:
        channel_data, programme_data = client.load(True)
        xbmcgui.Dialog().notification("ErsatzTV", L(32220).format(len(channel_data), len(programme_data)), xbmcgui.NOTIFICATION_INFO, 4000)
    except Exception as exc:
        xbmcgui.Dialog().ok("ErsatzTV", L(32221).format(exc))
    xbmc.executebuiltin("Container.Refresh")


def test_connection():
    try:
        channels_data, programmes = client.load(True)
        xbmcgui.Dialog().ok(L(32222), L(32223).format(len(channels_data), len(programmes)))
    except Exception as exc:
        xbmcgui.Dialog().ok(L(32222), L(32224).format(exc))


def run():
    params = dict(urllib.parse.parse_qsl(sys.argv[2][1:] if len(sys.argv) > 2 else ""))
    action = params.get("action", "home")
    try:
        if action == "home": home()
        elif action == "channels": channels(group=params.get("group"))
        elif action == "favorites": channels(favorites_only=True)
        elif action == "now": channels(now_only=True)
        elif action == "groups": groups()
        elif action == "guide": guide(params.get("id", ""))
        elif action == "play": play(params.get("stream", ""), params.get("name", "ErsatzTV"), params.get("logo", ""))
        elif action in ("favorite", "unfavorite"):
            client.set_favourite(params.get("id", ""), action == "favorite")
            xbmc.executebuiltin("Container.Refresh")
        elif action == "refresh": refresh()
        elif action == "test": test_connection()
        elif action == "settings": ADDON.openSettings()
        elif action == "server":
            from . import server
            server.home()
        elif action == "server_choose":
            from . import server
            server.choose_executable()
            xbmc.executebuiltin("Container.Refresh")
        elif action == "server_generate_key":
            from . import server
            server.generate_management_key()
            xbmc.executebuiltin("Container.Refresh")
        elif action == "server_start":
            from . import server
            server.start()
            xbmc.executebuiltin("Container.Refresh")
        elif action == "server_stop":
            from . import server
            server.stop()
            xbmc.executebuiltin("Container.Refresh")
        elif action == "server_restart":
            from . import server
            server.restart()
            xbmc.executebuiltin("Container.Refresh")
        elif action == "server_status":
            from . import server
            server.show_status()
        elif action == "server_log":
            from . import server
            server.show_log()
        elif action == "pvr":
            from . import pvr
            pvr.home()
        elif action == "pvr_configure":
            from . import pvr
            pvr.configure()
            xbmc.executebuiltin("Container.Refresh")
        elif action == "pvr_test":
            from . import pvr
            pvr.test_urls()
        elif action == "pvr_status":
            from . import pvr
            pvr.show_status()
        elif action == "pvr_settings":
            from . import pvr
            pvr.open_settings()
        elif action == "pvr_reload":
            from . import pvr
            pvr.reload_client()
        elif action == "pvr_kodi_settings":
            from . import pvr
            pvr.open_kodi_settings()
        elif action == "manage":
            from . import management
            management.home()
        elif action == "manage_test":
            from . import management
            management.test()
        elif action == "manage_section":
            from . import management
            management.section(params.get("section", "support"))
        elif action == "manage_sources":
            from . import management
            management.media_sources()
        elif action == "manage_web":
            from . import management
            management.server_page(params.get("path", ""), params.get("title", "ErsatzTV"))
        elif action == "manage_search":
            from . import management
            management.search(params.get("kind", "collections"), params.get("title", "Media"))
        elif action == "manage_audit":
            from . import management
            management.audit()
        elif action == "manage_list":
            from . import management
            management.listing(params.get("kind", "channels"))
        elif action == "manage_create":
            from . import management
            management.create(params.get("kind", "channels"))
        elif action == "manage_edit":
            from . import management
            management.edit(params.get("kind", "channels"), params.get("id", ""))
        elif action == "manage_delete":
            from . import management
            management.delete(params.get("kind", "channels"), params.get("id", ""), params.get("name", "item"))
        elif action == "manage_items":
            from . import management
            management.schedule_items(params.get("id", ""), params.get("name", "Schedule"))
        elif action == "manage_items_edit":
            from . import management
            management.edit_schedule_items(params.get("id", ""))
        elif action == "manage_external":
            from . import management
            management.external(params.get("kind", "profiles"))
        elif action in ("manage_external_create", "manage_external_edit", "manage_external_delete"):
            from . import management
            management.external_mutation(params.get("kind", "profiles"), action.rsplit("_", 1)[-1], params.get("id"), params.get("name", "item"))
        else: home()
    except Exception as exc:
        client.log("Unhandled error: {}".format(exc), xbmc.LOGERROR)
        xbmcgui.Dialog().ok("ErsatzTV", L(32225).format(exc))
        finish(cache=False)
