# ErsatzTV v26.5.1 feature coverage

The Kodi management menu follows the order and grouping in ErsatzTV's `MainLayout.razor`.

| ErsatzTV section | Kodi coverage |
| --- | --- |
| Channels | Native list/create/edit/delete; channel number, profile, group and advanced JSON fields |
| FFmpeg Profiles | Native list/create/edit/delete |
| Watermarks | Native list/create/edit/delete |
| Media Sources | Native source-type selector for Local, Emby, Jellyfin and Plex server-page handoffs |
| Media | Native TV show and artist search; server-page handoffs for libraries, trash, movies, videos, songs, images and remote streams |
| Lists | Native Smart Collection and Filler Preset CRUD; native searches for manual, multi- and rerun collections; server-page handoffs for full editors, playlists and Trakt lists |
| Scheduling | Native Schedule, Schedule Item, Block and Playout CRUD; server-page handoffs for Templates, Decos and Deco Templates |
| Settings | Server-page handoffs for FFmpeg, Logging, HDHomeRun, Scanner, Playout, UI and XMLTV; native Kodi add-on, local-server, IPTV Simple and PVR settings |
| Support | Native API connection/capability test and feature audit; server-page handoffs for health, logs and troubleshooting |

## Preserved local integration

- Select and launch a separately installed ErsatzTV executable.
- Start, stop, restart and monitor the Kodi-started process.
- View the local server log.
- Generate a 256-bit Kodi management API key.
- Pass the matching key to the local process through `ETV_KODI_MANAGEMENT_KEY`.
- Optionally start the server when the add-on opens.
- Install/enable IPTV Simple Client and populate its ErsatzTV M3U/XMLTV endpoints.
- Apply Kodi PVR channel-number and EPG-window options through JSON-RPC.
- Test IPTV endpoints, inspect status, open IPTV Simple settings and reload its data.

Server-page handoffs are intentional where ErsatzTV v26.5.1 has no stable management endpoint. The add-on never pretends an unsupported operation succeeded and never sends the management key in a URL.
