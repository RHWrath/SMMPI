# Install Guide

Use this guide to set up the system on your local machine, including dependencies.

W.I.P. This guide is under construction and will be updated with more detailed instructions soon.

## Dependencies (Windows)

Before running the project, make sure the following dependencies are installed on your system.

### 1. Install Python and `pip`

Download and install the latest version of Python:

https://www.python.org/downloads/windows/

During installation, make sure to enable:

- Add Python to PATH
- Install pip

Verify the installation:

```bash
python --version
pip --version
```

---

### 2. Install Android Debug Bridge (`adb`)

#### Option 1 (Recommended): Install via Android Studio

Download Android Studio:

https://developer.android.com/studio

Then:

1. Open Android Studio
2. Go to **SDK Manager**
3. Install:
   - Android SDK Platform-Tools

Verify installation:

```bash
adb version
```

#### Option 2: Install Platform Tools directly

https://developer.android.com/tools/releases/platform-tools

After extracting the ZIP file, add the folder to your system `PATH`.

---

### 3. Install FFmpeg

Install FFmpeg using `winget`:

```bash
winget install Gyan.FFmpeg
```

Verify installation:

```bash
ffmpeg -version
```

---

### 4. Verify Everything

Run the following commands to confirm all dependencies are installed correctly:

```bash
python --version
pip --version
adb version
ffmpeg -version
```

---
## Dependencies

OAuth2Bridge - https://www.nuget.org/packages/OAuth2Bridge/

Install with `dotnet restore`

## Utilizing Environment variables for API keys

Create a `.env` file in the root directory of the project and add your API keys in the following format:
```
KEY="VALUE"
```

Keys can be fetched from the _static EnvReader class_ under *Core/SMMPI.Applications/*

Platform specific API keys
-----
### Discord
```
DISCORD_CLIENT_ID=<val>
DISCORD_CLIENT_SECRET=<val>
DISCORD_REDIRECT_URI=<val>
DISCORD_AUTH_URL=<val>
```