import json
import urllib.parse
import webbrowser

import xbmc
import xbmcgui

from . import client


def _router():
    from . import router
    return router


def _notify(message, error=False):
    xbmcgui.Dialog().notification("ErsatzTV Manager", message,
                                  xbmcgui.NOTIFICATION_ERROR if error else xbmcgui.NOTIFICATION_INFO, 5000)


def _input(heading, default=""):
    return xbmcgui.Dialog().input(heading, defaultt=str(default or ""), type=xbmcgui.INPUT_ALPHANUM)


def _yesno(heading, message):
    return xbmcgui.Dialog().yesno(heading, message)


def _select(heading, labels, preselect=-1):
    return xbmcgui.Dialog().select(heading, labels, preselect=preselect)


def _page(data):
    return data.get("page", []) if isinstance(data, dict) else data or []


def _request(path, method="GET", payload=None, success="Saved"):
    try:
        result = client.api_request("/api/kodi-management/" + path.lstrip("/"), method, payload)
        if method != "GET":
            _notify(success)
        return result
    except Exception as exc:
        xbmcgui.Dialog().ok("ErsatzTV Manager", "Request failed:\n{}".format(exc))
        return None


def _json_edit(heading, value):
    raw = _input(heading, json.dumps(value, separators=(",", ":"), ensure_ascii=False))
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError as exc:
        xbmcgui.Dialog().ok("Invalid JSON", str(exc))
        return None


def home():
    r = _router()
    r.xbmcplugin.setPluginCategory(r.HANDLE, "ErsatzTV")
    r.item("Channels", r.url("manage_list", kind="channels"), True)
    r.item("FFmpeg profiles", r.url("manage_external", kind="profiles"), True)
    r.item("Watermarks", r.url("manage_list", kind="watermarks"), True)
    r.item("Media sources", r.url("manage_sources"), False)
    r.item("Media", r.url("manage_section", section="media"), True)
    r.item("Lists", r.url("manage_section", section="lists"), True)
    r.item("Scheduling", r.url("manage_section", section="scheduling"), True)
    r.item("Settings", r.url("manage_section", section="settings"), True)
    r.item("Support", r.url("manage_section", section="support"), True)
    r.finish(cache=False)


_SECTIONS = {
    "sources": ("Media sources", [
        ("Local", "web", "media/sources/local"),
        ("Emby", "web", "media/sources/emby"),
        ("Jellyfin", "web", "media/sources/jellyfin"),
        ("Plex", "web", "media/sources/plex"),
    ]),
    "media": ("Media", [
        ("Libraries", "web", "media/libraries"),
        ("Trash", "web", "media/trash"),
        ("TV shows", "search", "shows"),
        ("Movies", "web", "media/movies"),
        ("Music artists", "search", "artists"),
        ("Other videos", "web", "media/other/videos"),
        ("Songs", "web", "media/music/songs"),
        ("Images", "web", "media/browser/images"),
        ("Remote streams", "web", "media/remote/streams"),
    ]),
    "lists": ("Lists", [
        ("Manual collections", "search", "collections"),
        ("Smart collections", "native", "smart"),
        ("Multi-collections", "search", "multi-collections"),
        ("Rerun collections", "search", "rerun-collections"),
        ("Playlists", "web", "media/playlists"),
        ("Trakt lists", "web", "media/trakt/lists"),
        ("Filler presets", "list", "fillers"),
    ]),
    "scheduling": ("Scheduling", [
        ("Schedules", "list", "schedules"),
        ("Blocks", "list", "blocks"),
        ("Templates", "web", "templates"),
        ("Decos", "web", "decos"),
        ("Deco templates", "web", "deco-templates"),
        ("Playouts", "list", "playouts"),
    ]),
    "settings": ("Settings", [
        ("FFmpeg settings", "web", "settings/ffmpeg"),
        ("Logging", "web", "settings/logging"),
        ("HDHomeRun", "web", "settings/hdhr"),
        ("Scanner", "web", "settings/scanner"),
        ("Playout", "web", "settings/playout"),
        ("User interface", "web", "settings/ui"),
        ("XMLTV", "web", "settings/xmltv"),
        ("Server Configuration", "server", ""),
        ("PVR Configuration", "pvr", ""),
        ("Settings", "addon_settings", ""),
    ]),
    "support": ("Support", [
        ("Health checks", "web", "system/health"),
        ("Logs", "web", "system/logs"),
        ("Troubleshooting", "web", "system/troubleshooting"),
        ("Test management API", "test", ""),
        ("Feature coverage audit", "audit", ""),
    ]),
}


def section(name):
    r = _router()
    title, entries = _SECTIONS.get(name, ("ErsatzTV", []))
    r.xbmcplugin.setPluginCategory(r.HANDLE, title)
    for label, mode, target in entries:
        if mode == "list":
            path, folder = r.url("manage_list", kind=target), True
        elif mode == "native":
            path, folder = r.url("manage_external", kind=target), True
        elif mode == "search":
            path, folder = r.url("manage_search", kind=target, title=label), False
        elif mode == "web":
            path, folder = r.url("manage_web", path=target, title=label), False
        elif mode == "server":
            path, folder = r.url("server"), True
        elif mode == "pvr":
            path, folder = r.url("pvr"), True
        elif mode == "addon_settings":
            path, folder = r.url("settings"), False
        elif mode == "test":
            path, folder = r.url("manage_test"), False
        else:
            path, folder = r.url("manage_audit"), False
        r.item(label, path, folder)
    r.finish(cache=False)


def media_sources():
    sources = [
        ("Local", "media/sources/local"),
        ("Emby", "media/sources/emby"),
        ("Jellyfin", "media/sources/jellyfin"),
        ("Plex", "media/sources/plex"),
    ]
    selected = _select("Choose media source type", [label for label, _ in sources])
    if selected < 0:
        return
    label, path = sources[selected]
    server_page(path, "{} media sources".format(label))


def server_page(path, title):
    base = client.setting("server_url", "http://localhost:8409").rstrip("/")
    target = base + "/" + path.lstrip("/")
    opened = False
    try:
        opened = webbrowser.open(target)
    except Exception as exc:
        client.log("Unable to open browser for {}: {}".format(target, exc), xbmc.LOGERROR)
    message = "Opened in the system browser:\n\n{}" if opened else "Open this ErsatzTV page in a browser:\n\n{}"
    xbmcgui.Dialog().ok(title or "ErsatzTV", message.format(target))


def search(kind, title):
    query = _input("Search {}".format(title.lower()))
    if not query:
        return
    rows = _request("search/{}?{}".format(kind, urllib.parse.urlencode({"query": query})))
    if rows is None:
        return
    labels = []
    for row in rows:
        if isinstance(row, dict):
            labels.append(row.get("name") or row.get("title") or row.get("showTitle") or "Result {}".format(row.get("id", "")))
        else:
            labels.append(str(row))
    xbmcgui.Dialog().select("{} — {} result(s)".format(title, len(labels)), labels)


def audit():
    native = [
        "Channels", "FFmpeg profiles", "Watermarks", "Smart collections", "Filler presets",
        "Schedules and schedule items", "Blocks", "Playouts", "Content search",
        "Local server start/stop/restart/log", "Automatic management API key"
    ]
    server_pages = [
        "Local/Emby/Jellyfin/Plex sources", "Libraries and media browsers", "Trash", "Manual/multi/rerun collections",
        "Playlists and Trakt lists", "Templates, decos, and deco templates", "FFmpeg/logging/HDHomeRun/scanner/playout/UI/XMLTV settings",
        "Health checks, server logs, and troubleshooting"
    ]
    text = "NATIVE KODI CONTROLS\n• {}\n\nSERVER PAGE HANDOFFS\n• {}\n\nAll ErsatzTV v26.5.1 navigation areas are represented. Server page handoffs are used where ErsatzTV has no stable management API.".format(
        "\n• ".join(native), "\n• ".join(server_pages))
    xbmcgui.Dialog().textviewer("ErsatzTV feature coverage", text)


def test():
    result = _request("capabilities")
    if result:
        xbmcgui.Dialog().ok("ErsatzTV Manager", "Connected to management API v{}.\n\nFeatures:\n{}".format(
            result.get("apiVersion", "?"), "\n".join(result.get("features", []))))


def listing(kind):
    r = _router()
    titles = {"channels": "Channels", "schedules": "Schedules", "playouts": "Playouts", "blocks": "Block schedules",
              "fillers": "Filler presets", "watermarks": "Watermarks"}
    r.xbmcplugin.setPluginCategory(r.HANDLE, titles.get(kind, "ErsatzTV management"))
    r.item("[Add {}]".format(titles.get(kind, kind).rstrip("s")), r.url("manage_create", kind=kind), False)
    data = _request(kind)
    if data is None:
        return r.finish(cache=False)
    rows = _page(data)
    editor_paths = {
        "channels": "channels/{id}", "schedules": "schedules/{id}", "playouts": "playouts",
        "blocks": "blocks/{id}", "fillers": "media/filler/presets/{id}/edit", "watermarks": "watermarks/{id}"
    }
    for entity in rows:
        entity_id = entity.get("id", entity.get("playoutId"))
        if kind == "channels":
            label = "{} · {}".format(entity.get("number", "?"), entity.get("name", "Unnamed"))
        elif kind == "playouts":
            label = "{} · {}".format(entity.get("channelNumber", "?"), entity.get("channelName", entity.get("name", "Playout")))
        else:
            label = entity.get("name", entity.get("channelName", "{} {}".format(kind, entity_id)))
        context = [("Edit", "RunPlugin({})".format(r.url("manage_edit", kind=kind, id=entity_id))),
                   ("Delete", "RunPlugin({})".format(r.url("manage_delete", kind=kind, id=entity_id, name=label)))]
        editor_path = editor_paths.get(kind)
        if editor_path:
            context.append(("Open complete ErsatzTV editor", "RunPlugin({})".format(
                r.url("manage_web", path=editor_path.format(id=entity_id), title=label))))
        if kind == "schedules":
            context.insert(1, ("Edit schedule items", "Container.Update({})".format(r.url("manage_items", id=entity_id, name=label))))
        r.item(label, r.url("manage_edit", kind=kind, id=entity_id), False, context=context)
    if not rows:
        r.empty("No {} found.".format(titles.get(kind, kind).lower()))
    r.finish(cache=False)


def _profiles():
    try:
        return client.api_request("/api/ffmpeg/profiles") or []
    except Exception:
        return []


def _channel_payload(existing=None):
    model = dict(existing or {})
    name = _input("Channel name", model.get("name", "New Channel"))
    if not name:
        return None
    number = _input("Channel number", model.get("number", "1"))
    if not number:
        return None
    group = _input("Channel group", model.get("group", "ErsatzTV"))
    profiles = _profiles()
    if profiles:
        labels = [p.get("name", "Profile {}".format(p.get("id"))) for p in profiles]
        current = next((i for i, p in enumerate(profiles) if p.get("id") == model.get("ffmpegProfileId")), 0)
        choice = _select("FFmpeg profile", labels, current)
        if choice < 0:
            return None
        profile_id = profiles[choice].get("id")
    else:
        value = _input("FFmpeg profile ID", model.get("ffmpegProfileId", 1))
        if not value:
            return None
        profile_id = int(value)
    model.update({"name": name, "number": number, "group": group, "ffmpegProfileId": profile_id})
    defaults = {"categories": "", "slugSeconds": None, "logo": None, "externalLogoUrl": "",
                "streamSelectorMode": 0, "streamSelector": None, "preferredAudioLanguageCode": None,
                "preferredAudioTitle": None, "playoutSource": 0, "playoutMode": 0,
                "mirrorSourceChannelId": None, "playoutOffset": None, "streamingEngine": 0,
                "nextEngineTextSubtitleMode": 0, "streamingMode": 5, "watermarkId": None,
                "fallbackFillerId": None, "preferredSubtitleLanguageCode": None, "subtitleMode": 0,
                "musicVideoCreditsMode": 0, "musicVideoCreditsTemplate": None, "songVideoMode": 0,
                "transcodeMode": 0, "idleBehavior": 0, "isEnabled": True, "showInEpg": True}
    for key, value in defaults.items():
        model.setdefault(key, value)
    if not client.setting_bool("advanced_json", False):
        return model
    actions = ["Save" if existing else "Create", "Advanced channel fields"]
    choice = _select("Channel options", actions)
    return _json_edit("Edit complete channel JSON", model) if choice == 1 else model if choice == 0 else None


def _schedule_payload(existing=None):
    model = dict(existing or {})
    name = _input("Schedule name", model.get("name", "New Schedule"))
    if not name:
        return None
    model["name"] = name
    for key, label in (("keepMultiPartEpisodesTogether", "Keep multi-part episodes together?"),
                       ("treatCollectionsAsShows", "Treat collections as shows?"),
                       ("shuffleScheduleItems", "Shuffle schedule items?"),
                       ("randomStartPoint", "Use a random start point?")):
        model[key] = _yesno("Schedule", label) if key not in model else _yesno("Schedule", label)
    behavior = _select("Fixed start behavior", ["Strict", "Flexible"], int(model.get("fixedStartTimeBehavior", 0)))
    if behavior < 0:
        return None
    model["fixedStartTimeBehavior"] = behavior
    return model


def create(kind):
    if kind == "channels": payload = _channel_payload()
    elif kind == "schedules": payload = _schedule_payload()
    elif kind == "playouts": return create_playout()
    elif kind == "blocks":
        groups = _request("block-groups") or []
        if not groups:
            group_name = _input("New block group name", "Kodi")
            created = _request("block-groups", "POST", {"name": group_name}, "Block group created") if group_name else None
            groups = [created] if isinstance(created, dict) else []
        if not groups: return
        choice = _select("Block group", [g.get("name", "Group") for g in groups])
        if choice < 0: return
        block_name = _input("Block name", "New Block")
        payload = {"blockGroupId": groups[choice].get("id"), "name": block_name} if block_name else None
    else:
        templates = {
            "fillers": {"name": "New Filler", "fillerKind": 1, "fillerMode": 2, "count": 1,
                        "allowWatermarks": True, "collectionType": 0, "useChaptersAsMediaItems": False},
            "watermarks": {"name": "New Watermark", "image": None, "mode": 0, "imageSource": 0,
                           "location": 0, "size": 0, "width": 10.0, "horizontalMargin": 2.0,
                           "verticalMargin": 2.0, "frequencyMinutes": 0, "durationSeconds": 0,
                           "opacity": 100, "placeWithinSourceContent": False, "opacityExpression": None, "zIndex": 0}
        }
        payload = _json_edit("Create {} JSON".format(kind), templates.get(kind, {}))
    if payload is not None and _request(kind, "POST", payload, "Created") is not None:
        xbmc.executebuiltin("Container.Refresh")


def edit(kind, entity_id):
    entity = _request("{}/{}".format(kind, entity_id)) if kind in ("channels", "schedules") else None
    if entity is None:
        rows = _page(_request(kind) or [])
        entity = next((x for x in rows if str(x.get("id", x.get("playoutId"))) == str(entity_id)), None)
    if not entity:
        return
    if kind == "channels": payload = _channel_payload(entity)
    elif kind == "schedules": payload = _schedule_payload(entity)
    elif kind == "playouts":
        payload = _json_edit("Edit playout file JSON", {"kind": "scripted", "scheduleFile": entity.get("scheduleFile", "")})
        path = "playouts/{}/file".format(entity_id)
    elif kind == "blocks":
        details = _request("blocks/{}".format(entity_id))
        if not details: return
        block = details.get("block", {})
        payload = _json_edit("Edit complete block schedule JSON", {
            "blockGroupId": block.get("groupId"), "name": block.get("name"),
            "minutes": block.get("minutes", 30), "stopScheduling": block.get("stopScheduling", 0),
            "items": details.get("items", [])})
    else: payload = _json_edit("Edit complete {} JSON".format(kind), entity)
    if payload is not None:
        path = locals().get("path", "{}/{}".format(kind, entity_id))
        if _request(path, "PUT", payload, "Saved") is not None:
            xbmc.executebuiltin("Container.Refresh")


def delete(kind, entity_id, name):
    if client.setting_bool("confirm_destructive", True) and not _yesno("Delete {}?".format(kind.rstrip("s")), "Permanently delete {}?".format(name)):
        return
    if _request("{}/{}".format(kind, entity_id), "DELETE", success="Deleted") is not None:
        xbmc.executebuiltin("Container.Refresh")


def create_playout():
    channels = _request("channels") or []
    if not channels:
        return xbmcgui.Dialog().ok("Add playout", "Create a channel first.")
    choice = _select("Channel", ["{} · {}".format(c.get("number"), c.get("name")) for c in channels])
    if choice < 0: return
    kinds = ["classic", "block", "sequential", "scripted", "externalJson"]
    kind_choice = _select("Playout type", ["Classic schedule", "Block schedule", "Sequential file", "Scripted file", "External JSON file"])
    if kind_choice < 0: return
    payload = {"kind": kinds[kind_choice], "channelId": channels[choice].get("id"), "programScheduleId": None, "scheduleFile": None}
    if kind_choice == 0:
        schedules = _page(_request("schedules") or {})
        selected = _select("Schedule", [s.get("name") for s in schedules])
        if selected < 0: return
        payload["programScheduleId"] = schedules[selected].get("id")
    elif kind_choice in (2, 3, 4):
        payload["scheduleFile"] = _input("Schedule file path")
        if not payload["scheduleFile"]: return
    if _request("playouts", "POST", payload, "Playout created") is not None:
        xbmc.executebuiltin("Container.Refresh")


def schedule_items(schedule_id, name):
    r = _router()
    r.xbmcplugin.setPluginCategory(r.HANDLE, "{} — Items".format(name))
    items = _request("schedules/{}/items".format(schedule_id))
    if items is None:
        return r.finish(cache=False)
    r.item("[Edit complete item list]", r.url("manage_items_edit", id=schedule_id), False)
    for item in items:
        label = "{} · {} · {}".format(item.get("index", "?"), item.get("collectionName", "Schedule item"), item.get("playoutMode", ""))
        r.item(label, r.url("manage_items_edit", id=schedule_id), False)
    if not items:
        r.empty("No schedule items. Select the editor above to add them.")
    r.finish(cache=False)


def edit_schedule_items(schedule_id):
    items = _request("schedules/{}/items".format(schedule_id))
    if items is None: return
    payload = _json_edit("Edit complete schedule item list", [_schedule_item_payload(item) for item in items])
    if payload is not None and _request("schedules/{}/items".format(schedule_id), "PUT", payload, "Schedule items saved") is not None:
        xbmc.executebuiltin("Container.Refresh")


def _schedule_item_payload(item):
    """Convert the read model to ReplaceProgramScheduleItem's complete write model."""
    nested = lambda key, id_key="id": (item.get(key) or {}).get(id_key)
    return {
        "index": item.get("index", 0), "startType": item.get("startType", 1),
        "startTime": item.get("startTime"), "fixedStartTimeBehavior": item.get("fixedStartTimeBehavior"),
        "playoutMode": item.get("playoutMode", 2), "collectionType": item.get("collectionType", 0),
        "collectionId": nested("collection"), "multiCollectionId": nested("multiCollection"),
        "smartCollectionId": nested("smartCollection"), "rerunCollectionId": nested("rerunCollection"),
        "mediaItemId": nested("mediaItem", "mediaItemId"), "playlistId": nested("playlist"),
        "searchTitle": item.get("searchTitle"), "searchQuery": item.get("searchQuery"),
        "playbackOrder": item.get("playbackOrder", 3), "marathonGroupBy": item.get("marathonGroupBy", 0),
        "marathonShuffleGroups": item.get("marathonShuffleGroups", False),
        "marathonShuffleItems": item.get("marathonShuffleItems", False),
        "marathonBatchSize": item.get("marathonBatchSize"), "fillWithGroupMode": item.get("fillWithGroupMode", 0),
        "multipleMode": item.get("multipleMode", 0), "multipleCount": item.get("count", item.get("multipleCount")),
        "playoutDuration": item.get("playoutDuration"), "tailMode": item.get("tailMode", 0),
        "discardToFillAttempts": item.get("discardToFillAttempts"), "customTitle": item.get("customTitle"),
        "guideMode": item.get("guideMode", 0), "preRollFillerId": nested("preRollFiller"),
        "midRollFillerId": nested("midRollFiller"), "postRollFillerId": nested("postRollFiller"),
        "tailFillerId": nested("tailFiller"), "fallbackFillerId": nested("fallbackFiller"),
        "watermarkIds": [x.get("id") for x in item.get("watermarks", [])],
        "graphicsElementIds": [x.get("id") for x in item.get("graphicsElements", [])],
        "preferredAudioLanguageCode": item.get("preferredAudioLanguageCode"),
        "preferredAudioTitle": item.get("preferredAudioTitle"),
        "preferredSubtitleLanguageCode": item.get("preferredSubtitleLanguageCode"),
        "subtitleMode": item.get("subtitleMode")
    }


def external(kind):
    r = _router()
    path = "/api/ffmpeg/profiles" if kind == "profiles" else "/api/collections/smart"
    title = "FFmpeg profiles" if kind == "profiles" else "Smart collections"
    r.xbmcplugin.setPluginCategory(r.HANDLE, title)
    try: rows = client.api_request(path) or []
    except Exception as exc:
        xbmcgui.Dialog().ok("ErsatzTV Manager", str(exc)); rows = []
    r.item("[Add {}]".format("profile" if kind == "profiles" else "smart collection"), r.url("manage_external_create", kind=kind), False)
    for row in rows:
        label = row.get("name", "{} {}".format(title, row.get("id")))
        context = [("Edit", "RunPlugin({})".format(r.url("manage_external_edit", kind=kind, id=row.get("id")))),
                   ("Delete", "RunPlugin({})".format(r.url("manage_external_delete", kind=kind, id=row.get("id"), name=label)))]
        editor_path = "ffmpeg/{id}" if kind == "profiles" else "media/smart-collections/{id}/edit"
        context.append(("Open complete ErsatzTV editor", "RunPlugin({})".format(
            r.url("manage_web", path=editor_path.format(id=row.get("id")), title=label))))
        r.item(label, r.url("manage_external_edit", kind=kind, id=row.get("id")), False, context=context)
    if not rows: r.empty("No {} found.".format(title.lower()))
    r.finish(cache=False)


def external_mutation(kind, action, entity_id=None, name="item"):
    definitions = {
        "profiles": {"list": "/api/ffmpeg/profiles", "create": "/api/ffmpeg/profiles/new",
                     "update": "/api/ffmpeg/profiles/update", "delete": "/api/ffmpeg/delete/{}"},
        "smart": {"list": "/api/collections/smart", "create": "/api/collections/smart/new",
                  "update": "/api/collections/smart/update", "delete": "/api/collections/smart/delete/{}"}
    }
    paths = definitions[kind]
    try:
        rows = client.api_request(paths["list"]) or []
        entity = next((x for x in rows if str(x.get("id")) == str(entity_id)), {})
        if action == "delete":
            if client.setting_bool("confirm_destructive", True) and not _yesno("Delete?", "Permanently delete {}?".format(name)):
                return
            client.api_request(paths["delete"].format(entity_id), "DELETE")
        else:
            payload = _json_edit(("Create" if action == "create" else "Edit") + " complete JSON", entity)
            if payload is None: return
            client.api_request(paths[action], "POST" if action == "create" else "PUT", payload)
        _notify("Saved" if action != "delete" else "Deleted")
        xbmc.executebuiltin("Container.Refresh")
    except Exception as exc:
        xbmcgui.Dialog().ok("ErsatzTV Manager", "Request failed:\n{}".format(exc))
