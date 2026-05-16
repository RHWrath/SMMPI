namespace SMMPI.App.Services;

/// <summary>
/// Windows Forms based folder picker used by the WPF shell.
/// </summary>
public sealed class FolderBrowserPicker : IFolderPicker
{
    /// <summary>
    /// Opens a folder selection dialog and returns the selected path, or null when cancelled.
    /// </summary>
    public string? PickFolder(string title)
    {
        using var dialog = new System.Windows.Forms.FolderBrowserDialog
        {
            Description = title,
            UseDescriptionForTitle = true,
            ShowNewFolderButton = true
        };

        return dialog.ShowDialog() == System.Windows.Forms.DialogResult.OK
            ? dialog.SelectedPath
            : null;
    }
}
