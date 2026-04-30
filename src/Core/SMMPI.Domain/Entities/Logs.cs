using SMMPI.Domain.Enums;

namespace SMMPI.Infrastructure.Logging;

public abstract record Log(DateTime Timestamp);

public record LogEntry(LogCategory Category, DateTime Timestamp, Log LogRecord);

public record MediaLog(byte[] Data, string MimeType, DateTime Timestamp)
    : Log(Timestamp)
{
    public override string ToString() => $"MimeType: {MimeType}, Timestamp:[{Timestamp:HH:mm:ss}]";
}
public record ChatLog(string Content, string UserId, DateTime Timestamp)
: Log(Timestamp)
{
    public override string ToString() => $"UID: {UserId}, Content:{Content}, Timestamp:[{Timestamp:HH:mm:ss}]";
}
public record UserLog(string UserId, string Username, DateOnly MemberSince, string connections, DateTime Timestamp)
: Log(Timestamp)
{
    public override string ToString() => $"UID: {UserId},Username: {Username}, MemberSince: {MemberSince}, " +
        $"Connections: {connections}, Timestamp:[{Timestamp:HH:mm:ss}]";
}
