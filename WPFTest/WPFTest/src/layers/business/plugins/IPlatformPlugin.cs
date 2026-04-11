namespace Layers.Business.Plugins
{
    interface IPlatformPlugin
    {
        string PlatformName { get; }
        void connect(string device_id);
        void SendMessage(Payload payload);
        void SendMessage(Payload payload, String mediaFilepath); // Send message with / without attachment
    }
}