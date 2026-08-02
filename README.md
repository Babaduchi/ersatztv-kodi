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

Install `repository.babaduchi.ersatztv-1.0.0.zip` once from the [Babaduchi ErsatzTV Kodi Repository](https://babaduchi.github.io/ersatztv-kodi/). Then select **Add-ons > Install from repository > Babaduchi ErsatzTV Repository > Video add-ons > ErsatzTV**. Kodi will discover later versions published by this repository.

The **Publish Kodi repository** GitHub Actions workflow rebuilds `addons.xml`, checksums, versioned add-on ZIPs, and the repository installer on GitHub Pages after every successful build from the release branch.

## Automated builds

Open the repository's **Actions** tab and select **Build and validate**. Successful runs publish an installable Kodi ZIP directly on the matching GitHub release and provide a compiled companion artifact. The ZIP contains `plugin.video.ersatztv` at its root, as Kodi requires. The Docker job also verifies that the custom ErsatzTV image builds successfully.

## Security

The companion API is disabled unless `ETV_KODI_MANAGEMENT_KEY` is configured. Use a long random secret, keep ErsatzTV on a trusted network, and use a separate value for the streaming JWT.

See `ersatztv-kodi-companion/README.md` for container instructions and back up the ErsatzTV `/config` directory before replacing an existing container.
