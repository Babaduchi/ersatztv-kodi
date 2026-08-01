# ErsatzTV Kodi management companion

This adds an authenticated management API to ErsatzTV legacy v26.5.x. It uses ErsatzTV's existing MediatR commands, validators and transaction handlers; it does not access the database directly.

## Build

```sh
docker build --build-arg ERSATZTV_VERSION=v26.5.1 -t ersatztv-kodi:v26.5.1 .
```

Run it with the same volumes and environment as the official ErsatzTV container, plus a strong random management key:

```sh
-e ETV_KODI_MANAGEMENT_KEY='replace-with-a-long-random-secret'
```

Enter that same key in the Kodi add-on. The management API is disabled when the variable is absent. Keep port 8409 on a trusted network or place it behind an authenticated reverse proxy. Streaming JWT and the management key are intentionally separate credentials.
