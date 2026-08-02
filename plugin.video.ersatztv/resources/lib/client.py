import gzip
import hashlib
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import xbmc
import xbmcaddon
import xbmcvfs

from .model import Channel, Programme


ADDON = xbmcaddon.Addon()
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
_ATTR = re.compile(r'([\w-]+)="([^"]*)"')


class ManagementApiUnavailable(RuntimeError):
    """The server answered, but does not provide the Kodi management API."""


def setting(key, default=""):
    value = ADDON.getSetting(key)
    return value if value != "" else default


def setting_bool(key, default=False):
    raw = setting(key, "true" if default else "false")
    return raw.lower() == "true"


def log(message, level=xbmc.LOGINFO):
    if level != xbmc.LOGDEBUG or setting_bool("debug_logging"):
        xbmc.log("[ErsatzTV] {}".format(message), level)


def endpoint(path_or_url):
    if path_or_url.startswith(("http://", "https://")):
        result = path_or_url
    else:
        result = urllib.parse.urljoin(setting("server_url", "http://localhost:8409").rstrip("/") + "/", path_or_url.lstrip("/"))
    token = setting("jwt_token")
    if token:
        parsed = urllib.parse.urlsplit(result)
        query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        if not any(key == "access_token" for key, _ in query):
            query.append(("access_token", token))
        result = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(query), parsed.fragment))
    return result


def _cache_path(url):
    if not xbmcvfs.exists(PROFILE):
        xbmcvfs.mkdirs(PROFILE)
    return os.path.join(PROFILE, "cache-{}.bin".format(hashlib.sha256(url.encode("utf-8")).hexdigest()))


def clear_cache():
    if not xbmcvfs.exists(PROFILE):
        return
    for name in xbmcvfs.listdir(PROFILE)[1]:
        if name.startswith("cache-"):
            xbmcvfs.delete(os.path.join(PROFILE, name))


def fetch(url, force=False):
    cache_path = _cache_path(url)
    ttl = int(setting("cache_minutes", "15")) * 60
    if not force and ttl and xbmcvfs.exists(cache_path) and time.time() - os.path.getmtime(cache_path) < ttl:
        with open(cache_path, "rb") as handle:
            return handle.read()
    request = urllib.request.Request(url, headers={"User-Agent": "Kodi-ErsatzTV/1.0", "Accept-Encoding": "gzip"})
    context = None
    if url.startswith("https://") and not setting_bool("verify_tls", True):
        context = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(request, timeout=int(setting("timeout", "15")), context=context) as response:
            data = response.read()
            if response.headers.get("Content-Encoding") == "gzip":
                data = gzip.decompress(data)
        with open(cache_path, "wb") as handle:
            handle.write(data)
        return data
    except (urllib.error.URLError, OSError) as exc:
        log("Request failed for {}: {}".format(url, exc), xbmc.LOGERROR)
        if setting_bool("fallback_cache", True) and xbmcvfs.exists(cache_path):
            with open(cache_path, "rb") as handle:
                return handle.read()
        raise


def api_request(path, method="GET", payload=None):
    url = urllib.parse.urljoin(setting("server_url", "http://localhost:8409").rstrip("/") + "/", path.lstrip("/"))
    headers = {"User-Agent": "Kodi-ErsatzTV/2.0", "Accept": "application/json"}
    key = setting("management_key")
    if key:
        headers["X-ErsatzTV-Kodi-Key"] = key
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    context = None
    if url.startswith("https://") and not setting_bool("verify_tls", True):
        context = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(request, timeout=int(setting("timeout", "15")), context=context) as response:
            body = response.read()
            if not body:
                return True
            text = body.decode("utf-8-sig", "replace")
            content_type = (response.headers.get("Content-Type") or "").lower()
            try:
                return json.loads(text)
            except (TypeError, ValueError):
                if "text/html" in content_type or text.lstrip().startswith(("<!DOCTYPE", "<html", "<head", "<body")):
                    raise ManagementApiUnavailable(
                        "This ErsatzTV server does not include the Kodi management API. "
                        "Install and run the authenticated ErsatzTV Kodi companion build, or use the standard ErsatzTV web editor.")
                preview = " ".join(text.strip().split())[:160]
                raise RuntimeError("The management API returned invalid JSON{}{}".format(
                    ": " if preview else ".", preview))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError("HTTP {}: {}".format(exc.code, detail or exc.reason))


def parse_m3u(data):
    lines = data.decode("utf-8-sig", "replace").splitlines()
    channels = []
    metadata = None
    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF:"):
            head, sep, name = line.partition(",")
            attrs = dict(_ATTR.findall(head))
            metadata = (attrs, name.strip() if sep else attrs.get("tvg-name", "Channel"))
        elif line and not line.startswith("#") and metadata:
            attrs, name = metadata
            channel_id = attrs.get("tvg-id") or attrs.get("channel-id") or name
            channels.append(Channel(
                id=channel_id, name=attrs.get("tvg-name") or name, url=line,
                number=attrs.get("tvg-chno") or attrs.get("channel-number", ""),
                logo=attrs.get("tvg-logo", ""), group=attrs.get("group-title", "")
            ))
            metadata = None
    return channels


def _xmltv_time(value):
    value = (value or "").strip()
    match = re.match(r"(\d{14})(?:\s*([+-]\d{4}|Z))?", value)
    if not match:
        raise ValueError("Invalid XMLTV date: {}".format(value))
    base = datetime.strptime(match.group(1), "%Y%m%d%H%M%S")
    offset = match.group(2)
    if offset and offset != "Z":
        sign = 1 if offset[0] == "+" else -1
        minutes = sign * (int(offset[1:3]) * 60 + int(offset[3:5]))
        from datetime import timedelta
        return base.replace(tzinfo=timezone(timedelta(minutes=minutes))).astimezone()
    return base.replace(tzinfo=timezone.utc).astimezone()


def _text(node, name):
    child = node.find(name)
    return (child.text or "").strip() if child is not None and child.text else ""


def parse_xmltv(data, minimum=None, maximum=None):
    programmes = []
    root = ET.fromstring(data)
    for node in root.findall("programme"):
        try:
            start, stop = _xmltv_time(node.get("start")), _xmltv_time(node.get("stop"))
        except ValueError:
            continue
        if minimum and stop < minimum:
            continue
        if maximum and start > maximum:
            continue
        icon = node.find("icon")
        programmes.append(Programme(
            channel_id=node.get("channel", ""), start=start, stop=stop,
            title=_text(node, "title") or "Untitled", subtitle=_text(node, "sub-title"),
            description=_text(node, "desc"), category=[(x.text or "").strip() for x in node.findall("category") if x.text],
            icon=icon.get("src", "") if icon is not None else "", episode=_text(node, "episode-num")
        ))
    return programmes


def load(force=False):
    from datetime import timedelta
    now = datetime.now().astimezone()
    channels = parse_m3u(fetch(endpoint(setting("m3u_path", "/iptv/channels.m3u")), force))
    minimum = now - timedelta(hours=int(setting("past_hours", "2")))
    maximum = now + timedelta(hours=int(setting("future_hours", "12")))
    programmes = parse_xmltv(fetch(endpoint(setting("xmltv_path", "/iptv/xmltv.xml")), force), minimum, maximum)
    return channels, programmes


def favourites():
    try:
        return set(json.loads(setting("favourites", "[]")))
    except (TypeError, ValueError):
        return set()


def set_favourite(channel_id, enabled):
    values = favourites()
    values.add(channel_id) if enabled else values.discard(channel_id)
    ADDON.setSetting("favourites", json.dumps(sorted(values)))
