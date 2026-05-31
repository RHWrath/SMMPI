namespace SMMPI.App.Services;

/// <summary>
/// Abstraction for choosing folders from the WPF view model layer.
/// </summary>
public interface IFolderPicker
{
    /// <summary>
    /// Opens a folder picker with the supplied title and returns the selected path.
    /// </summary>
    string? PickFolder(string title);
}
