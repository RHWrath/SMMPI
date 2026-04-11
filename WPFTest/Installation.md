# Install Guide

Use this guide to set up the system on your local machine, including dependencies.

W.I.P. This guide is under construction and will be updated with more detailed instructions soon.

## Dependencies

OAuth2Bridge - https://www.nuget.org/packages/OAuth2Bridge/

Install with `dotnet restore`

## Utilizing Environment variables for API keys

Create a `.env` file in the root directory of the project and add your API keys in the following format:
```
KEY="VALUE"
```

Keys can be fetched from the _static EnvReader class_ under *Layers/Tools*

Platform specific API keys
-----
### Discord
```
DISCORD_CLIENT_ID=<val>
DISCORD_CLIENT_SECRET=<val>
DISCORD_REDIRECT_URI=<val>
DISCORD_AUTH_URL=<val>
```