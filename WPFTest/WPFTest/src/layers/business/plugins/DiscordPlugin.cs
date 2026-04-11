using System.Net.Http;
using System.Net.Http.Headers;
using System.Text.Json;

namespace Layers.Business.Plugins
{
    class DiscordPlugin : IPlatformPlugin
    {
        public string PlatformName => "Discord";
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

        public void Authenticate()
        {

        }
    }
}
