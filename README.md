# ErsatzTV for Kodi

An unofficial Kodi add-on for watching and managing an [ErsatzTV](https://ersatztv.org/) lineup from a Kodi-native interface.

The add-on reads ErsatzTV's standard M3U playlist and XMLTV guide, plays channels without requiring a PVR client, and can configure Kodi's official IPTV Simple Client for full Live TV integration. Optional channel-building and scheduling controls are available when ErsatzTV is running the authenticated Kodi management companion included in this project.

- Current add-on version: **2.3.5**
- Provider: **Babaduchi**
- Compatibility: **Kodi 19 or newer (Python 3)** on macOS, Windows, and Linux
- Management companion target: **ErsatzTV legacy v26.5.1**

## Project components

| Component | Purpose |
| --- | --- |
| `plugin.video.ersatztv` | Installable Kodi video add-on |
| `ersatztv-kodi-companion` | Optional authenticated management API and container build for ErsatzTV legacy v26.5.1 |
| `FEATURE_COVERAGE.md` | Detailed native-control and server-page coverage matrix |
| `.github/workflows/build.yml` | Validates and packages the Kodi add-on and companion builds |

Automatic updates are distributed by the separate [Babaduchi Kodi Repository](https://github.com/Babaduchi/kodi-repository).

## Features

### Watching and guide data

- Browse all channels, channel groups, favourites, and channels currently on air.
- Display current and next programme information from XMLTV.
- Open a per-channel programme guide.
- Play ErsatzTV streams with Kodi's normal player.
- Optionally use InputStream Adaptive for HLS.
- Cache playlist and guide data, with optional stale-cache fallback when the server is unavailable.
- Configure guide range, sorting, channel numbers, artwork, hidden groups, time format, and playback MIME type inside Kodi.

### PVR Configuration

The **PVR Configuration** menu can:

- Install or enable Kodi's official IPTV Simple Client.
- Populate the ErsatzTV M3U and XMLTV URLs automatically.
- Preserve an optional streaming JWT in generated URLs.
- Enable backend channel ordering and channel numbering.
- Configure Kodi's past and future EPG windows.
- Test both IPTV endpoints.
- Show IPTV Simple status and open its settings.
- Reload IPTV Simple and PVR data.

The setup displays the exact URLs before changing anything and asks before replacing a different existing IPTV Simple configuration. Restart Kodi once if channels do not appear immediately after the first setup.

### Server Configuration

The add-on does **not** bundle ErsatzTV. Point **Server Configuration** at a separately installed ErsatzTV executable to:

- Test the configured server connection.
- Start, stop, or restart a process launched by Kodi.
- Monitor process and network status.
- View the Kodi-started server log.
- Start ErsatzTV automatically when the add-on opens.
- Generate a cryptographically random Kodi management API key.

When Kodi starts ErsatzTV, it supplies the generated key through `ETV_KODI_MANAGEMENT_KEY`. Kodi can only stop or restart a process that it started itself.

### Channel & Schedule Configuration

The management navigation follows ErsatzTV's own major sections:

- Channels
- FFmpeg profiles
- Watermarks
- Media sources
- Media
- Lists
- Scheduling
- Settings
- Support

Native management includes guided and advanced editors for supported channels, schedules, schedule items, playouts, blocks, filler presets, watermarks, FFmpeg profiles, smart collections, and content searches. Media Sources uses a Kodi selector for Local, Emby, Jellyfin, or Plex before opening the corresponding ErsatzTV editor.

Some ErsatzTV features do not expose a stable management endpoint. Those entries open the corresponding standard ErsatzTV web editor instead of pretending the action was completed inside Kodi. See [FEATURE_COVERAGE.md](FEATURE_COVERAGE.md) for the complete breakdown.

## Installation

### Recommended: automatic updates

1. Download the latest repository installer from [Babaduchi Kodi Repository releases](https://github.com/Babaduchi/kodi-repository/releases/latest).
2. Do not unzip the downloaded file.
3. In Kodi, open **Settings → Add-ons → Install from zip file**.
4. Select `repository.babaduchi.ersatztv-<version>.zip`.
5. Open **Install from repository → Babaduchi Kodi Repository → Video add-ons → ErsatzTV**.
6. Select **Install**.
7. For unattended updates, set **Settings → System → Add-ons → Updates → Install updates automatically**.

### Manual installation

Download `plugin.video.ersatztv-<version>.zip` from the [latest ErsatzTV Kodi release](https://github.com/Babaduchi/ersatztv-kodi/releases/latest), then use **Settings → Add-ons → Install from zip file**. Do not unzip it and do not download the GitHub Actions artifact wrapper.

Manual installation does not provide automatic updates unless the Babaduchi Kodi Repository is also installed.

## Initial configuration

1. Start ErsatzTV separately or configure **Server Configuration** to launch its executable.
2. Open **ErsatzTV → Settings → Connection**.
3. Set **Server URL**. For another computer, use its LAN address, such as `http://192.168.1.50:8409`; `localhost` only refers to the computer running Kodi.
4. Keep the default paths `/iptv/channels.m3u` and `/iptv/xmltv.xml`, or replace them with the exact URLs shown by ErsatzTV.
5. Leave **Streaming JWT access token** blank unless JWT streaming protection was intentionally enabled in ErsatzTV.
6. Open **Server Configuration → Test server connection**.
7. Optionally open **PVR Configuration → Configure IPTV Simple automatically**.

The bottom of the main add-on menu is ordered as:

1. **PVR Configuration**
2. **Channel & Schedule Configuration**
3. **Settings**

**Refresh Guide** remains with the normal viewing and guide actions.

## Management companion requirement

Playback, guide browsing, favourites, IPTV Simple setup, and PVR configuration work with a standard ErsatzTV installation.

Native channel and schedule editing requires the companion build in `ersatztv-kodi-companion`. Standard ErsatzTV does not provide `/api/kodi-management`. If the server returns its HTML application for that path, the add-on detects it, explains that the companion is unavailable, and offers to open the normal ErsatzTV editor. It no longer displays a raw `Expecting value` JSON error.

The companion uses ErsatzTV's existing commands and validators; it does not write directly to the database. See [ersatztv-kodi-companion/README.md](ersatztv-kodi-companion/README.md) for build and container instructions.

## Authentication and security

The two optional credentials serve different purposes:

| Credential | Purpose | Normally required? |
| --- | --- | --- |
| Streaming JWT access token | Protects M3U, XMLTV, and video-stream URLs | No; leave blank unless JWT streaming security is enabled in ErsatzTV |
| Kodi management API key | Protects channel-building and scheduling operations | Only when using the management companion |

The management key must match `ETV_KODI_MANAGEMENT_KEY` on the companion server. It is intentionally separate from the streaming JWT and is sent in an HTTP header, never in a management URL.

Keep ErsatzTV on a trusted network or behind an authenticated HTTPS reverse proxy. Do not commit tokens, keys, Kodi settings, ErsatzTV configuration, or media-library information to GitHub. Back up ErsatzTV's `/config` directory before replacing an existing container.

## Troubleshooting

### `Errno 61: Connection refused`

Nothing is listening at the configured Server URL. Start ErsatzTV and confirm the hostname, port, and firewall. If ErsatzTV runs on another computer, replace `localhost` with that computer's LAN IP address.

### `Expecting value: line ...`

Older add-on versions displayed this when standard ErsatzTV returned HTML for the missing Kodi management API. Update to version 2.3.5 or newer. Native management still requires the companion; the updated add-on provides a clear explanation and web-editor fallback.

### Kodi reports an invalid ZIP structure

Download the direct release asset whose name starts with `plugin.video.ersatztv-` or `repository.babaduchi.ersatztv-`. Do not unzip it, rename an HTML download as `.zip`, or install a nested GitHub Actions artifact. Published packages are checked for a single correct root folder, `addon.xml`, nested archives, and ZIP integrity.

### Channels do not appear in Kodi Live TV

Use **PVR Configuration → Test ErsatzTV M3U and XMLTV URLs**, then reload IPTV Simple. Confirm that the URLs use an address reachable from the Kodi computer. Restart Kodi once after the initial IPTV Simple configuration.

### Automatic updates are not appearing

Confirm that **Babaduchi Kodi Repository** is installed and enabled, then open its context menu and select **Check for updates**. The standalone repository index is hosted at `https://babaduchi.github.io/kodi-repository/`.

## Builds and development

GitHub Actions validates Python and XML, creates a Kodi-installable ZIP, checks its root structure and nested archives, compiles the companion against pinned ErsatzTV legacy v26.5.1 source, and verifies the companion container build.

The add-on uses Python's standard library and Kodi APIs. For local development, place `plugin.video.ersatztv` in Kodi's `addons` directory. Keep the add-on version in `addon.xml` synchronized with any published release.

## License

MIT. See [plugin.video.ersatztv/LICENSE](plugin.video.ersatztv/LICENSE).
