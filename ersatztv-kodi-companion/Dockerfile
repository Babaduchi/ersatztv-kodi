ARG ERSATZTV_VERSION=v26.5.1
FROM alpine/git AS source
ARG ERSATZTV_VERSION
RUN git clone --depth 1 --branch "$ERSATZTV_VERSION" https://github.com/ErsatzTV/legacy.git /src
COPY ErsatzTV/Controllers/Api/KodiManagementController.cs /src/ErsatzTV/Controllers/Api/KodiManagementController.cs

FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
ENV DOTNET_NUGET_SIGNATURE_VERIFICATION=false
COPY --from=source /src /src
WORKDIR /src
RUN dotnet publish ErsatzTV/ErsatzTV.csproj -c Release -o /app --no-self-contained -p:NuGetAudit=false

FROM ghcr.io/ersatztv/legacy:${ERSATZTV_VERSION}
WORKDIR /app
COPY --from=build /app .
EXPOSE 8409
ENTRYPOINT ["dotnet", "ErsatzTV.dll"]
