# ErsatzTV for Kodi

Kodi-native playback, channel building, and scheduling for ErsatzTV legacy v26.5.x.

This repository contains:

- `plugin.video.ersatztv`: installable Kodi 19+ add-on
- `ersatztv-kodi-companion`: authenticated management API and custom-container build
- GitHub Actions validation for the Kodi package, .NET companion, and Docker image

## Kodi Live TV setup

Open **ErsatzTV > PVR Configuration > Configure IPTV Simple automatically**. The guided setup can install and enable Kodi's official IPTV Simple Client, populate the ErsatzTV M3U playlist and XMLTV guide URLs, enable backend channel numbering, and size Kodi's EPG window from the add-on guide settings.

The setup shows the exact URLs before making changes and asks again before replacing a different existing IPTV Simple configuration. Use the test and status entries in the same menu to diagnose connectivity. If Kodi does not expose channels immediately after first configuration, restart Kodi once.

## Automatic updates in Kodi

Install the repository ZIP from the standalone [Babaduchi Kodi Repository](https://github.com/Babaduchi/kodi-repository). Then select **Video add-ons → ErsatzTV**. Kodi will discover later versions published there.

## Automated builds

Open the repository's **Actions** tab and select **Build and validate**. Successful runs publish an installable Kodi ZIP directly on the matching GitHub release and provide a compiled companion artifact. The ZIP contains `plugin.video.ersatztv` at its root, as Kodi requires. The Docker job also verifies that the custom ErsatzTV image builds successfully.

## Security

The companion API is disabled unless `ETV_KODI_MANAGEMENT_KEY` is configured. Use a long random secret, keep ErsatzTV on a trusted network, and use a separate value for the streaming JWT.

See `ersatztv-kodi-companion/README.md` for container instructions and back up the ErsatzTV `/config` directory before replacing an existing container.

## Management API requirement

Native channel and schedule editing requires the authenticated companion build in `ersatztv-kodi-companion`. A standard ErsatzTV installation does not expose `/api/kodi-management`; when it is detected, the add-on explains the requirement and offers to open the corresponding standard ErsatzTV web editor instead of displaying a JSON decoding error.
