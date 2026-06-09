# Builden voor release

Dit document beschrijft hoe een **Windows release-ZIP** voor stakeholders wordt gebouwd: lokaal via de terminal, versiebeheer, en welke onderdelen bijgewerkt moeten worden wanneer de applicatie of mappenstructuur wijzigt.

De lokale build en de GitHub Actions-workflow volgen **dezelfde stappen** (publish → bundelen → ZIP). Alleen de upload naar GitHub Releases vindt plaats in CI.

---

## Vereisten

- **Windows** (voor lokaal builden)
- **.NET SDK 10** (`dotnet --version`)
- Volledig uitgecheckte repository **SMMPI**, inclusief:
  - `tools/` (ADB, scrcpy, …)
  - `packages/Prototype/ffmpeg/` (ffmpeg.exe, ffprobe.exe)

De mappen `artifacts/` en bestanden `SMMPI-Operator-windows-v*.zip` staan in `.gitignore` en worden **niet** gecommit.

---

## Lokaal builden (terminal)

Open een terminal in de **root van de SMMPI-repository** (locatie van `SMMPI.sln`).

### Standaard build (versie 1.0.0)

```powershell
.\scripts\build-release.ps1
```

### Specifieke versie

```powershell
.\scripts\build-release.ps1 -Version "1.0.1"
```

### Clone-pad met spaties

Gebruik de CMD-wrapper; deze quotet paden correct:

```bat
scripts\build-release.cmd
```

Met versie (argumenten worden doorgegeven aan het PowerShell-script):

```bat
scripts\build-release.cmd -Version "1.0.1"
```

### Werking van het script

1. Controleert of verplichte bestanden in `tools/` en `packages/Prototype/ffmpeg/` aanwezig zijn.
2. Voert `dotnet publish` uit op het WPF-project (self-contained, **win-x64**).
3. Bundelt publish-output, `tools/`, FFmpeg en `docs/Opstarten.md` in `artifacts/release-root/`.
4. Genereert `SMMPI-Operator-windows-v{versie}.zip` in de repository-root.

### Output

| Pad | Beschrijving |
|-----|----------------|
| `SMMPI-Operator-windows-v1.0.0.zip` | Distributiebestand voor stakeholder / WeTransfer |
| `artifacts/release-root/` | Uitgepakte map voor lokale acceptatietest (`SMMPI.exe`) |
| `artifacts/publish/` | Ruwe `dotnet publish`-output (tussenresultaat) |

Voor lokale acceptatie: start `artifacts\release-root\SMMPI.exe` (telefoon via USB; zie `docs/Opstarten.md`).

---

## Versie verhogen

De releaseversie staat **niet** automatisch in de assembly; deze bepaalt primair de **ZIP-naam** en (bij CI) de **Git-tag**.

### Lokaal

Geef `-Version` mee aan het script:

```powershell
.\scripts\build-release.ps1 -Version "1.1.0"
```

Resultaat: `SMMPI-Operator-windows-v1.1.0.zip`.

De standaardversie staat in `scripts/build-release.ps1` bij `param([string]$Version = "1.0.0")`. Deze default dient bij een nieuwe afgesproken basisversie te worden bijgewerkt.

### GitHub Actions (draft release)

1. Wijzigingen pushen naar [RHWrath/SMMPI](https://github.com/RHWrath/SMMPI).
2. **Actions → Release Windows (SMMPI Operator) → Run workflow** uitvoeren.
3. Versie invullen (bijv. `1.1.0`) → de workflow maakt tag `v1.1.0` en een **draft** release met de ZIP.

De workflow-default staat in `.github/workflows/release-windows.yml` onder `workflow_dispatch.inputs.version.default`.

### Overige locaties met versie-informatie

| Locatie | Doel |
|---------|------|
| `scripts/build-release.ps1` | Default `-Version` en ZIP-naam |
| `.github/workflows/release-windows.yml` | Workflow-input default, tag, release-titel |
| `docs/Opstarten.md` | Voorbeeld-ZIP-naam in stakeholderdocumentatie |

Er is momenteel geen centrale `Version`-eigenschap in het `.csproj`; assembly-versie en release-versie kunnen daardoor uiteenlopen totdat versiebeheer wordt gecentraliseerd.

---

## Release via GitHub Actions

De workflow `.github/workflows/release-windows.yml` roept hetzelfde script aan als de lokale build (`scripts/build-release.ps1`) en uploadt daarna de ZIP naar GitHub Releases.

- Trigger: handmatig (`workflow_dispatch`)
- Authenticatie: ingebouwde `GITHUB_TOKEN` — **geen** handmatig aan te maken secret of Personal Access Token voor releases in dezelfde repository
- Vereiste repository-instelling: **Settings → Actions → General → Workflow permissions → Read and write permissions**
- Release wordt aangemaakt als **draft**; publicatie geschiedt handmatig op de Releases-pagina

### Eerste GitHub Release publiceren

#### 1. Voorwaarden controleren

- Workflow-bestand staat op de remote: `.github/workflows/release-windows.yml`
- Script en assets staan op de remote: `scripts/build-release.ps1`, `tools/`, `packages/Prototype/ffmpeg/`, `docs/Opstarten.md`
- Schrijfrechten op de repository (collaborator of eigenaar)

#### 2. Workflow permissions instellen (eenmalig)

1. Open `https://github.com/RHWrath/SMMPI`
2. **Settings** → **Actions** → **General**
3. Onder **Workflow permissions**: kies **Read and write permissions**
4. **Save**

Er hoeft **geen** token in **Settings → Secrets and variables → Actions** te worden geplaatst. GitHub levert per workflow-run automatisch `GITHUB_TOKEN` met de rechten uit deze instelling.

Een **Personal Access Token (PAT)** is alleen nodig bij bijvoorbeeld releases naar een **andere** repository, of wanneer organisatiebeleid de standaard token beperkt.

#### 3. Workflow starten

1. Tab **Actions**
2. Linkermenu: **Release Windows (SMMPI Operator)**
3. **Run workflow**
4. Branch kiezen (meestal `main` of de branch waar de workflow op staat)
5. Versie invullen (eerste release: `1.0.0`)
6. **Run workflow** bevestigen

De run duurt enkele minuten (publish + ZIP + draft release).

#### 4. Draft controleren en publiceren

1. **Actions** → de run openen → alle stappen moeten groen zijn
2. **Releases** (rechterkant van de repository, of `https://github.com/RHWrath/SMMPI/releases`)
3. Draft **SMMPI Operator v1.0.0 (Windows)** openen
4. ZIP downloaden en lokaal testen (`SMMPI.exe`, `Opstarten.md`)
5. **Publish release** om de draft zichtbaar te maken voor anderen met toegang tot de repository

Voor stakeholders **zonder** GitHub-toegang: ZIP downloaden uit de draft/release en delen via WeTransfer of interne distributie.

#### 5. Veelvoorkomende fouten bij de eerste run

| Fout | Oorzaak | Oplossing |
|------|---------|-----------|
| Workflow niet zichtbaar onder Actions | Bestand niet gepusht of op verkeerde branch | Workflow committen en pushen naar de default branch |
| `Resource not accessible by integration` | Workflow permissions op Read-only | Read and write permissions inschakelen (stap 2) |
| `Missing files required for release packaging` | `tools/` of FFmpeg niet in git | Bestanden committen en opnieuw pushen |
| Tag `v1.0.0` already exists | Eerdere run met dezelfde versie | Nieuwe versie kiezen, of bestaande tag/release op GitHub verwijderen |
| `fail_on_unmatched_files` | ZIP niet aangemaakt | Build-stap in de log openen; `dotnet publish`-fout oplossen |

---

## Troubleshooting

### Veelvoorkomende buildfouten

| Symptoom | Mogelijke oorzaak | Actie |
|----------|-------------------|--------|
| `Missing files required for release packaging` | `tools/` of FFmpeg ontbreekt lokaal / niet gecommit | Paden in de foutmelding controleren; mappen aanvullen of checklist in het script bijwerken |
| `dotnet publish` faalt | SDK te oud, ontbrekende restore | .NET 10 SDK installeren; `dotnet restore` uitvoeren |
| Applicatie start niet na uitpakken | Alleen `SMMPI.exe` gekopieerd; `tools/` of `packages/` ontbreekt | Volledige ZIP uitpakken; mapstructuur intact laten |
| ZIP onverwacht groot | Self-contained publish (normaal ~150+ MB) | Verwacht gedrag; geen aparte .NET-runtime op de doel-pc vereist |

### Onderhoud bij wijzigingen in de applicatie

De workflow roept **`scripts/build-release.ps1`** aan. Wijzigingen aan de build-stappen horen **primair in het script**; de workflow bevat alleen trigger, .NET-setup en upload naar GitHub Releases. Bij wijzigingen aan paden of bundeling het script bijwerken — de workflow hoeft dan meestal niet aangepast te worden, tenzij de ZIP-naam of release-metadata wijzigt.

| Wijziging | Aan te passen bestanden | Details |
|-----------|-------------------------|---------|
| **WPF-project verplaatst of hernoemd** | `build-release.ps1` (`dotnet publish …`) | Pad naar het te publiceren `.csproj` (huidig: `src/Presentation/SMMPI.App/SMMPI.App.csproj`) |
| **Uitvoerbestand hernoemd** (`AssemblyName` in csproj) | `build-release.ps1` (verwijzing naar exe-naam), `docs/Opstarten.md`, eventueel workflow release-tekst | Huidig: `SMMPI.exe` via `<AssemblyName>SMMPI</AssemblyName>` |
| **`tools/` verplaatst of hernoemd** | `$required`-lijst en copy-stap in `build-release.ps1` | Tevens **applicatiecode**: `ToolPathService`, `AdbLocator` — runtime- en release-pad moeten overeenkomen (`{ancestor}/tools/`) |
| **Bestand toegevoegd of verwijderd in `tools/`** | `$required`-array in `build-release.ps1` | Alles wat `ToolPathService.EnsureScrcpyAvailable()` vereist, hoort in de release-`tools/` map |
| **FFmpeg verplaatst** (huidig: `packages/Prototype/ffmpeg/`) | Copy-stappen + `$required` in script | Tevens **applicatiecode**: `FfmpegLocator` — bundled pad `packages/Prototype/ffmpeg/` |
| **Nieuwe runtime-map naast de exe** | Extra `Copy-Item`-stap in script | Controleren of de applicatie paden relatief t.o.v. `AppContext.BaseDirectory` verwacht |
| **Stakeholder-readme hernoemd** | `Copy-Item "docs/Opstarten.md" …` in script | Doelnaam in ZIP (huidig: `Opstarten.md`) |
| **Target framework gewijzigd** (`net10.0-windows`) | Workflow `dotnet-version`; lokaal passende SDK | Publish-commando blijft doorgaans ongewijzigd |
| **Platform/RID** (huidig: `win-x64`) | `-r win-x64` in publish; ZIP-naam eventueel | ARM64 vereist aparte RID en acceptatietest |
| **Self-contained aan/uit** | `--self-contained true/false` in script | Stakeholder-build: huidig **self-contained** |
| **ZIP-bestandsnaam-patroon** | `$zipName` in script; `files:` in `release-windows.yml` | Huidig: `SMMPI-Operator-windows-v{versie}.zip` |
| **Standaard releaseversie** | `param($Version = …)` in script; workflow `default: '…'` | Zie sectie [Versie verhogen](#versie-verhogen) |
| **.NET SDK-versie op CI** | `release-windows.yml` → `setup-dotnet` `dotnet-version` | Huidig: `10.0.x` |

### Afstemming tussen code en release-script

De applicatie resolveert runtime-tools als volgt:

- **ADB / scrcpy:** map `tools/` naast of boven de executable — zie `ToolPathService`, `AdbLocator`.
- **FFmpeg / ffprobe:** `packages/Prototype/ffmpeg/` of systeem-PATH — zie `FfmpegLocator`, `FfmpegCommandBuilder`.

Wanneer in de **code** een ander bundled pad wordt geïntroduceerd, moet **`build-release.ps1`** worden bijgewerkt zodat die map in de ZIP wordt opgenomen. Zonder die aanpassing kan de applicatie in development nog functioneren (via PATH of afwijkende layout), maar niet in de stakeholder-ZIP.

### Validatie na wijzigingen

1. Lokaal: `.\scripts\build-release.ps1` uitvoeren en `artifacts\release-root\SMMPI.exe` testen.
2. Bij wijzigingen aan de workflow: test-run op GitHub Actions (draft release).

---

## Conclusie

Een stakeholder-build wordt lokaal opgebouwd vanuit de repository-root met `.\scripts\build-release.ps1` (optioneel `-Version`). Op GitHub roept de workflow hetzelfde script aan en publiceert een draft release. De resulterende ZIP bevat `Opstarten.md`. Bij wijzigingen in projectstructuur, tools of documentatie dient de onderhoudstabel te worden doorlopen; de build-logica staat in het script.

---

## Bronnen

- `scripts/build-release.ps1` — lokale build en CI-build
- `scripts/build-release.cmd` — wrapper bij paden met spaties
- `.github/workflows/release-windows.yml` — draft release op GitHub
- `docs/Opstarten.md` — instructies in de ZIP voor de stakeholder
- `README.md` — verwijzing naar dit document
