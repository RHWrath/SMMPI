using System.Windows;

namespace SMMPI.App.Views;

/// <summary>
/// Reusable settings and phone status panel for the operator shell.
/// </summary>
public partial class SettingsPanel
{
    public static readonly RoutedEvent ToggleRecordingRequestedEvent = EventManager.RegisterRoutedEvent(
        nameof(ToggleRecordingRequested),
        RoutingStrategy.Bubble,
        typeof(RoutedEventHandler),
        typeof(SettingsPanel));

    /// <summary>
    /// Raised when the operator asks to start or stop a recording.
    /// </summary>
    public event RoutedEventHandler ToggleRecordingRequested
    {
        add => AddHandler(ToggleRecordingRequestedEvent, value);
        remove => RemoveHandler(ToggleRecordingRequestedEvent, value);
    }

    /// <summary>
    /// Initializes the reusable settings panel.
    /// </summary>
    public SettingsPanel()
    {
        InitializeComponent();
    }

    /// <summary>
    /// Converts the local recording button click into a routed event for the shell.
    /// </summary>
    private void ToggleRecording_Click(object sender, RoutedEventArgs e)
    {
        RaiseEvent(new RoutedEventArgs(ToggleRecordingRequestedEvent));
    }
}
