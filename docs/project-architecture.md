# SMMPI - Projectstructuur en gebruik

Dit project bevat de nieuwe opzet voor de **Social Media Masking for Police Investigations** applicatie.  
De applicatie wordt opgebouwd als een modulaire WPF-desktopapplicatie in C#/.NET.

Het doel van deze structuur is om de applicatie overzichtelijk, testbaar en uitbreidbaar te maken.  
Omdat het project meerdere onderdelen bevat, zoals Android-aansturing, screen logging, rapportage en platformplugins, is gekozen voor een duidelijke scheiding tussen lagen.

---

## Projectstructuur

De solution is als volgt opgebouwd:

- src
  - Core
    - SMMPI.Application
    - SMMPI.Domain
  - Infrastructure
    - SMMPI.Infrastructure.Adb
    - SMMPI.Infrastructure.Logging
    - SMMPI.Infrastructure.Plugins
    - SMMPI.Infrastructure.Reporting
  - Presentation
    - SMMPI.App
- tests

---

## Waarom deze structuur?

Deze structuur past goed bij het project omdat de applicatie meerdere verantwoordelijkheden heeft:

- gebruikersinterface via WPF;
- Android-device aansturing via ADB;
- live preview / streaming;
- screen logging;
- opslag van bewijsmateriaal;
- rapportage/export;
- ondersteuning voor meerdere social media-platformen via plugins.

Door deze onderdelen te scheiden, voorkomen we dat alle logica in één groot WPF-project terechtkomt.  
Hierdoor wordt het project beter onderhoudbaar, makkelijker te testen en eenvoudiger uit te breiden.

---

## Uitleg per laag

### `Presentation`

Locatie:

src/Presentation/SMMPI.App

Dit is de WPF-applicatie die de gebruiker ziet en bedient.

Hier komen onder andere:

- `Views`
- `ViewModels`
- `App.xaml`
- `MainWindow.xaml`
- UI-binding
- gebruikersinteractie

De WPF-app mag gebruikersacties afhandelen, maar moet zo min mogelijk technische logica bevatten.

Niet wenselijk in de WPF-laag:
```
Process.Start("adb", "devices");
```
Beter:
```
await _deviceController.SearchDevicesAsync();
```
---

### `Core`

Locatie:

src/Core

De `Core` bevat de kern van de applicatie.  
Deze laag mag niet afhankelijk zijn van WPF, ADB, PDF-libraries of lokale bestandsopslag.

#### `SMMPI.Domain`

Hier staan de belangrijkste modellen, interfaces en basisconcepten van de applicatie.

Voorbeelden:

- SMMPI.Domain
  - Entities
    - AndroidDevice.cs
    - EvidenceItem.cs
    - LogEntry.cs
    - TargetData.cs
    
  - Interfaces
    - IDeviceController.cs
    - IEvidenceRepository.cs
    - IPlatformPlugin.cs
    - IReportService.cs

  - Enums
    - LogCategory.cs

Deze laag bevat vooral de afspraken en modellen van het systeem.

Voorbeeld:
```
public interface IReportService
{
    Task GenerateReportAsync(TargetData targetData);
}
```
---

#### `SMMPI.Application`

Hier staat de applicatielogica.  
Deze laag bepaalt wat er gebeurt wanneer een gebruiker een actie uitvoert.

Voorbeelden:

SMMPI.Application
-  Services
   - DeviceController.cs
   - StreamController.cs
   - PluginController.cs
   - RecordingService.cs
   - CaseWorkflowService.cs

Deze laag gebruikt interfaces uit `SMMPI.Domain`.

Voorbeeld:
```
public class RecordingService
{
    private readonly IScreenRecorder _screenRecorder;
    private readonly IEvidenceRepository _evidenceRepository;

    public RecordingService(
        IScreenRecorder screenRecorder,
        IEvidenceRepository evidenceRepository)
    {
        _screenRecorder = screenRecorder;
        _evidenceRepository = evidenceRepository;
    }
}
```
---

### `Infrastructure`

Locatie:

src/Infrastructure

De `Infrastructure`-laag bevat technische implementaties.  
Alles wat afhankelijk is van externe tools, bestanden, ADB, PDF-export of platformspecifieke code hoort hier thuis.

---

#### `SMMPI.Infrastructure.Adb`

Deze laag bevat alles wat direct met ADB communiceert.

Voorbeelden:

SMMPI.Infrastructure.Adb
 - AdbService.cs
 - AdbCommandRunner.cs
 - AdbDeviceDetector.cs
 - ScrcpyStreamService.cs

Hier mogen commando’s staan zoals:

- adb devices
- adb exec-out screencap -p
- adb push
- adb shell input

Deze logica hoort niet in de WPF-app, omdat ADB een technisch detail is.

---

#### `SMMPI.Infrastructure.Logging`

Deze laag bevat de concrete implementatie voor logging en opslag van bewijsmateriaal.

Voorbeelden:

SMMPI.Infrastructure.Logging
- FileEvidenceRepository.cs
- JsonLogWriter.cs
- LocalStorageService.cs

Hier wordt bijvoorbeeld geregeld dat logs, screenshots of recordings lokaal worden opgeslagen.

---

#### `SMMPI.Infrastructure.Reporting`

Deze laag bevat de rapportagefunctionaliteit.

Voorbeelden:

SMMPI.Infrastructure.Reporting
- PdfReportService.cs
- ReportBuilder.cs
- ReportExportOptions.cs

De rest van de applicatie hoeft niet te weten hoe een PDF technisch wordt gemaakt.  
Die roept alleen de interface `IReportService` aan.

---

#### `SMMPI.Infrastructure.Plugins`

Deze laag bevat platform-specifieke implementaties.

Voorbeelden:

SMMPI.Infrastructure.Plugins
- Snapchat
  - SnapchatPlugin.cs
- Discord
  - DiscordPlugin.cs
- WhatsApp
  - WhatsAppPlugin.cs

Hierdoor kunnen we later platformen toevoegen zonder de hele applicatie om te bouwen.

---

## Project references

De afhankelijkheden tussen de projecten horen ongeveer zo te lopen:

| Project | Heeft een reference naar | Waarom |
|---|---|---|
| `SMMPI.App` | `SMMPI.Application` | De WPF-app gebruikt de applicatielogica. |
| `SMMPI.App` | `SMMPI.Infrastructure.Adb` | Nodig om ADB-functionaliteit te registreren en gebruiken. |
| `SMMPI.App` | `SMMPI.Infrastructure.Logging` | Nodig om logging en opslag te registreren. |
| `SMMPI.App` | `SMMPI.Infrastructure.Reporting` | Nodig om rapportagefunctionaliteit te registreren. |
| `SMMPI.App` | `SMMPI.Infrastructure.Plugins` | Nodig om platformplugins beschikbaar te maken. |
| `SMMPI.Application` | `SMMPI.Domain` | De applicatielogica gebruikt de modellen en interfaces uit de domain-laag. |
| `SMMPI.Infrastructure.Adb` | `SMMPI.Domain` | De ADB-implementatie gebruikt interfaces en modellen uit de domain-laag. |
| `SMMPI.Infrastructure.Logging` | `SMMPI.Domain` | De logging-implementatie gebruikt domain-modellen zoals logs en evidence. |
| `SMMPI.Infrastructure.Reporting` | `SMMPI.Domain` | De rapportage-implementatie gebruikt domain-modellen en rapportage-interfaces. |
| `SMMPI.Infrastructure.Plugins` | `SMMPI.Domain` | Platformplugins implementeren interfaces uit de domain-laag. |


Belangrijke regel:

> `SMMPI.Domain` mag geen afhankelijkheid hebben op andere projecten.

De domain-laag is de kern van het systeem en moet onafhankelijk blijven van WPF, ADB, logging en reporting.