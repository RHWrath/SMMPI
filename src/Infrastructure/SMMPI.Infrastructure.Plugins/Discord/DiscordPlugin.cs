using Microsoft.Extensions.Logging;
using Newtonsoft.Json;
using OAuth2Bridge;
using SMMPI.Domain.Entities;
using SMMPI.Domain.Interfaces;

namespace SMMPI.Infrastructure.Plugins.Discord;

public class DiscordPlugin : IPlatformPlugin
{
    public string PlatformName => "Discord";

    public string ClientID => Environment.GetEnvironmentVariable("DISCORD_CLIENT_ID")?.Trim().Trim('"');

    public string ClientSecret => Environment.GetEnvironmentVariable("DISCORD_CLIENT_SECRET")?.Trim().Trim('"');

    public int port => 4444;

    public void connect(string device_id)
    {
        // Implement connection logic to Discord API using device_id (e.g., bot token or user credentials).
        // This is a placeholder for actual connection code.
        Console.WriteLine($"Connecting to Discord with device ID: {device_id}");
    }
    public void SendMessage(Payload payload)
    {
        // Implement message sending logic to Discord API using the payload information.
        // This is a placeholder for actual message sending code.
        Console.WriteLine($"Sending message to {payload.Recipient} on Discord: {payload.Message}");
    }
    public void SendMessage(Payload payload, string mediaFilepath)
    {
        // Implement message sending logic with media attachment to Discord API using the payload and media file path.
        // This is a placeholder for actual message sending code with media support.
        Console.WriteLine($"Sending message to {payload.Recipient} on Discord: {payload.Message} with media: {mediaFilepath}");
    }

    public async Task Authenticate()
    {
        var logger = LoggerFactory.Create(builder => builder.AddConsole())
            .CreateLogger<OAuthLogger>();

        var oAuthLogger = new OAuthLogger(logger);

        // Create the OAuth server instance
        var server = Tools.OAuthServer.CreateServer(ClientID, ClientSecret, port, oAuthLogger, PlatformName);

        // Add necessary Discord scopes
        server.Scopes.Add(DiscordScopes.Email);
        server.Scopes.Add(DiscordScopes.Identify);

        try
        {
            // Start the authentication process
            var userInfo = await server.AuthenticateAsync(CancellationToken.None, @"../../../../../../success.html");
            Console.WriteLine(JsonConvert.SerializeObject(userInfo, Formatting.Indented));
        }
        catch (OAuthException ex)
        {
            Console.WriteLine($"Authentication failed: {ex.Message}");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"An unexpected error occurred: {ex.Message}");
        }
    }
}