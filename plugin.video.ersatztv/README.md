# ErsatzTV for Kodi

A Kodi-native video add-on for browsing and playing an ErsatzTV lineup. It reads the standard M3U and XMLTV endpoints published by ErsatzTV, and does not require IPTV Simple Client.

## Features

- Channels with current and next programme metadata
- Per-channel programme guide
- Channel groups and add-on favourites
- Kodi-native connection, JWT, guide, playback, artwork and cache settings
- HLS through Kodi's player, with optional InputStream Adaptive
- Cached/offline guide fallback and an in-app connection test
- Kodi 19+ (Python 3)

## Install

1. In Kodi, choose **Add-ons → Install from zip file**.
2. Select the packaged Kodi ZIP from the latest GitHub Release.
3. Open **Add-ons → Video add-ons → ErsatzTV → Settings**.
4. Enter the ErsatzTV address (typically `http://SERVER:8409`). The default endpoint paths are `/iptv/channels.m3u` and `/iptv/xmltv.xml`; replace them with the exact URLs shown in ErsatzTV if needed.
5. If ErsatzTV protects streaming with JWT, paste the token in the streaming token setting.

## Native channel builder and scheduler

Version 2 includes an optional Kodi-native management interface. It requires the companion server patch shipped alongside the add-on and a matching `ETV_KODI_MANAGEMENT_KEY`. Channels and schedules have guided editors; every advanced ErsatzTV field remains available through opt-in complete JSON editors. Destructive actions require confirmation by default.

## Local server control

Version 2.1 adds a **Local ErsatzTV server** screen. Point it at a separately installed ErsatzTV executable to start, stop, restart, monitor, and view its log from Kodi. Windows, macOS, and Linux are supported. The server is intentionally not bundled inside the small Kodi add-on archive.

When Kodi starts a local server, it automatically generates a cryptographically random management API key when needed, stores it in Kodi's private add-on settings, and supplies the matching `ETV_KODI_MANAGEMENT_KEY` environment variable to ErsatzTV. Remote servers still require manual key configuration.

## Development

The add-on uses only Python's standard library and Kodi APIs. Install the folder directly into Kodi's `addons` directory for development. See `tests/` for parser tests that run outside Kodi.

## License

MIT
