using SMMPI.Domain.Enums;
using SMMPI.Infrastructure.Logging;

namespace SMMPI.Domain.Entities;

public class TargetData
{
    internal List<LogEntry> Logs { get; } = new();

    private void AddLog(LogCategory category, Log log)
    {
        Logs.Add(new LogEntry(category, DateTime.Now, log));
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