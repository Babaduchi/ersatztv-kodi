# ErsatzTV for Kodi

Kodi-native playback, channel building, and scheduling for ErsatzTV legacy v26.5.x.

This repository contains:

- `plugin.video.ersatztv`: installable Kodi 19+ add-on
- `ersatztv-kodi-companion`: authenticated management API and custom-container build
- GitHub Actions validation for the Kodi package, .NET companion, and Docker image

## Automated builds

Open the repository's **Actions** tab and select **Build and validate**. Successful runs provide an installable Kodi ZIP and a compiled companion artifact. The Docker job also verifies that the custom ErsatzTV image builds successfully.

## Security

The companion API is disabled unless `ETV_KODI_MANAGEMENT_KEY` is configured. Use a long random secret, keep ErsatzTV on a trusted network, and use a separate value for the streaming JWT.

See `ersatztv-kodi-companion/README.md` for container instructions and back up the ErsatzTV `/config` directory before replacing an existing container.

