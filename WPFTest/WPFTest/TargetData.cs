using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection.Metadata;
using System.Text;
using System.Threading.Tasks;

namespace SMM.Data  // Bundles like Kotlin package
{
    public enum LogCategory
    {
        Chat,     
        User,     
        Recording,
        Error         
    }

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

    public class TargetData
    {
        internal List<LogEntry> Logs { get; } = new();

        private void AddLog(LogCategory category, Log log)
        {
            Logs.Add(new LogEntry(category,DateTime.Now,log));
        }

        public void Feed(LogCategory category, Log? log)
        {
            switch ((category, log))
            {
                case (LogCategory.Chat, ChatLog cl):
                    AddLog(LogCategory.Chat, cl);
                    break;
                case (LogCategory.User, UserLog ul):
                    AddLog(LogCategory.User, ul);
                    break;
                case (LogCategory.Recording, MediaLog ml):
                    AddLog(LogCategory.Recording, ml);
                    break;
            }
        }

        public IEnumerable<LogEntry> ExtractLogs(LogCategory category)
        {
            return Logs
                .Where(entry => entry.Category == category)
                .Select(entry => entry)
                .Where(data => data != null)!;
        }
    }
}
