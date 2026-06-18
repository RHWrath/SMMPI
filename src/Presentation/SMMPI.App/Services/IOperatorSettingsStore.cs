namespace SMMPI.App.Services;

/// <summary>
/// Loads and saves operator preferences for the WPF shell.
/// </summary>
public interface IOperatorSettingsStore
{
    OperatorSettings Load();

    void Save(OperatorSettings settings);
}
