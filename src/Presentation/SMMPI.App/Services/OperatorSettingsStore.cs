using System.IO;
using System.Text.Json;

namespace SMMPI.App.Services;

/// <summary>
/// Stores operator preferences locally so the app can restore them on the next startup.
/// </summary>
public sealed class OperatorSettingsStore : IOperatorSettingsStore
{
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };
    private readonly string _settingsPath;

    /// <summary>
    /// Creates a settings store under the current Windows user's application data folder.
    /// </summary>
    public OperatorSettingsStore()
        : this(null)
    {
    }

    /// <summary>
    /// Creates a settings store that writes to the supplied file path, or the default AppData path when null.
    /// </summary>
    public OperatorSettingsStore(string? settingsFilePath)
    {
        _settingsPath = string.IsNullOrWhiteSpace(settingsFilePath)
            ? BuildDefaultSettingsPath()
            : settingsFilePath;
    }

    private static string BuildDefaultSettingsPath()
    {
        var appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
        var folder = string.IsNullOrWhiteSpace(appData)
            ? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".smmpi")
            : Path.Combine(appData, "SMMPI");
        return Path.Combine(folder, "operator-settings.json");
    }

    /// <summary>
    /// Loads the last saved operator settings, or an empty settings object when none exist yet.
    /// </summary>
    public OperatorSettings Load()
    {
        try
        {
            if (!File.Exists(_settingsPath))
            {
                return new OperatorSettings();
            }

            var json = File.ReadAllText(_settingsPath);
            return JsonSerializer.Deserialize<OperatorSettings>(json) ?? new OperatorSettings();
        }
        catch
        {
            return new OperatorSettings();
        }
    }

    /// <summary>
    /// Saves the supplied operator settings for the current Windows user.
    /// </summary>
    public void Save(OperatorSettings settings)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(_settingsPath)!);
        var json = JsonSerializer.Serialize(settings, JsonOptions);
        File.WriteAllText(_settingsPath, json);
    }
}

/// <summary>
/// Persisted operator fields that should survive closing and reopening the app.
/// </summary>
public sealed class OperatorSettings
{
    public string? OfficerName { get; set; }
    public string? CaseNumber { get; set; }
    public string? MediaLibraryFolder { get; set; }
    public string? CaseLogFolder { get; set; }
}
