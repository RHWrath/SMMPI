using SMMPI.Domain.Interfaces;

namespace SMMPI.Infrastructure.Logging;

public sealed class FileSessionLogService : ISessionLogService
{
    private readonly List<string> _events = [];

    public string CaseLogFolder { get; set; } =
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "SMMPI", "Logs");

    public async Task LogAsync(string message, CancellationToken cancellationToken)
    {
        Directory.CreateDirectory(CaseLogFolder);
        var line = $"{DateTimeOffset.Now:O} {message}";
        _events.Add(line);
        await File.AppendAllTextAsync(Path.Combine(CaseLogFolder, "session.log"), line + Environment.NewLine, cancellationToken);
    }

    public async Task<string> ExportSummaryAsync(CancellationToken cancellationToken)
    {
        Directory.CreateDirectory(CaseLogFolder);
        var path = Path.Combine(CaseLogFolder, $"session-summary-{DateTimeOffset.Now:yyyyMMdd-HHmmss}.md");
        var content = "# SMMPI Session Export" + Environment.NewLine + Environment.NewLine +
                      string.Join(Environment.NewLine, _events.Select(e => $"- {e}"));
        await File.WriteAllTextAsync(path, content, cancellationToken);
        return path;
    }
}
