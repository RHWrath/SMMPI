using SMMPI.Domain.Entities;

namespace SMMPI.Domain.Interfaces;

public interface IPlatformPlugin
{
    string PlatformName { get; }

    string ClientID { get; }
    string ClientSecret { get; }
    int port { get; }

    void connect(string device_id);
    void SendMessage(Payload payload);
    void SendMessage(Payload payload, String mediaFilepath); // Send message with / without attachment
}
