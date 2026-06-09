# SMMPI Operator — korte installatie (stakeholder)

Deze map bevat een **zelfstandige Windows-versie** van de SMMPI Operator. U hoeft **geen Python** te installeren en geen aparte build-stappen uit te voeren.

## Vereisten

- **Windows 10 of 11 (64-bit)**
- Een **Android-telefoon** met USB-debugging ingeschakeld
- Een **USB-kabel** (bij voorkeur datakabel, geen alleen-laden kabel)

## Installatie

1. Download het release-ZIP-bestand van GitHub (bijv. `SMMPI-Operator-windows-v1.0.0.zip`).
2. Pak het ZIP-bestand uit naar een map naar keuze (bijv. `C:\SMMPI`).
3. Laat de mapstructuur intact staan: de mappen `tools` en `packages` horen **naast** `SMMPI.exe` te staan.

## Starten

Dubbelklik op **`SMMPI.exe`**.

Verplaats of verwijder de mappen `tools` en `packages` niet; de applicatie zoekt daarin ADB, scrcpy en FFmpeg.

## Eerste gebruik met telefoon

1. Sluit de telefoon aan via USB.
2. Accepteer op de telefoon de vraag **USB-debugging toestaan** (indien gevraagd).
3. Open in de app het instellingenpaneel en kies het juiste apparaat.
4. Controleer of de live stream zichtbaar wordt.

## Wat zit er in dit pakket?

| Onderdeel | Doel |
| ----------- | ------------------------------------------------- |
| `SMMPI.exe` | Hoofdapplicatie (operatorinterface) |
| `tools/` | ADB en scrcpy (apparaat en schermstream) |
| `packages/Prototype/ffmpeg/` | FFmpeg en FFprobe voor preview en mediaverwerking |

## Instellingen en dossiers

- Operatorgegevens (naam, zaaknummer, mappen) worden per **Windows-gebruiker** opgeslagen onder `%AppData%\SMMPI\`.
- Sessielogs en opnames worden opgeslagen in de door u gekozen werkmappen in de app.

## Problemen?

| Probleem | Mogelijke oplossing |
| ----------------------- | ---------------------------------------------------------------------------------- |
| Geen apparaat zichtbaar | USB-debugging aan, kabel/data, `adb` autoriseren op telefoon |
| scrcpy / stream fout | Controleer of `tools` naast de exe staat en compleet is |
| Media versturen mislukt | Controleer of `packages/Prototype/ffmpeg` naast de exe staat |
| App start niet | Alleen Windows x64; uitpakken op lokale schijf (niet vanaf netwerkshare blokkeren) |

## Ondersteuning

Neem bij vragen contact op met het projectteam van Fontys / Politie Rotterdam.

*Versie en builddatum staan op de GitHub Releases-pagina van het SMMPI-repository.*
