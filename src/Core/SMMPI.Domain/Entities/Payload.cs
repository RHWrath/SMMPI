namespace SMMPI.Domain.Entities;

public class Payload
{
    public string Recipient { get; set; }
    public string Message { get; set; }
#nullable enable
    private byte[] MediaContent { get; set; } // IPlatformPlugin interface extends media content support.

    public Payload(string recipient, string message)
    {
        Recipient = recipient;
        Message = message;
    }
}