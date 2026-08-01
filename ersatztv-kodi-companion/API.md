# Kodi management API v1

Every request requires `X-ErsatzTV-Kodi-Key`. The server returns 503 until `ETV_KODI_MANAGEMENT_KEY` is configured.

| Area | Operations |
|---|---|
| Capabilities | `GET /api/kodi-management/capabilities` |
| Channels | list, detail, create, replace, delete |
| Classic schedules | list, detail, create, replace, delete |
| Schedule items | list and atomic full replacement |
| Playouts | list; create classic, block, sequential, scripted, or external JSON; update file; delete |
| Block schedules | groups; list, detail/items, create, atomic replace, delete |
| Fillers | list, create, replace, delete |
| Watermarks | list, create, replace, delete |
| Content lookup | collections, multi/smart/rerun collections, shows, seasons, artists |

ErsatzTV's existing endpoints continue to handle FFmpeg profiles and smart collections. The Kodi client includes them in the same management menu.

Atomic replacement is intentional for ordered schedule and block items: validation occurs before ErsatzTV commits the new list.
