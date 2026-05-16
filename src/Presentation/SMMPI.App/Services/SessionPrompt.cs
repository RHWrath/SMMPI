using System.IO;
using System.Windows;
using System.Windows.Controls;
using WinForms = System.Windows.Forms;

namespace SMMPI.App.Services;

/// <summary>
/// Captures the values needed to start a Python-backed case session.
/// </summary>
public sealed record SessionPromptResult(string OfficerName, string CaseNumber, string CaseRoot);

/// <summary>
/// Startup dialog for choosing the officer name, case number, and root folder for evidence.
/// </summary>
public sealed class SessionPrompt : Window
{
    private readonly System.Windows.Controls.TextBox _officer = new();
    private readonly System.Windows.Controls.TextBox _caseNumber = new();
    private readonly System.Windows.Controls.TextBox _caseRoot = new();
    private readonly System.Windows.Controls.ListBox _cases = new();

    public SessionPromptResult? Result { get; private set; }

    /// <summary>
    /// Builds the session dialog and preloads existing cases from the default case root.
    /// </summary>
    public SessionPrompt()
    {
        Title = "SMMPI-sessie starten";
        Width = 560;
        Height = 520;
        MinWidth = 480;
        MinHeight = 420;
        WindowStartupLocation = WindowStartupLocation.CenterScreen;

        var root = new Grid { Margin = new Thickness(20) };
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        root.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

        var title = new TextBlock
        {
            Text = "Medewerker en zaak",
            FontSize = 20,
            Margin = new Thickness(0, 0, 0, 18),
        };
        root.Children.Add(title);

        var officerPanel = LabeledControl("Naam medewerker", _officer);
        Grid.SetRow(officerPanel, 1);
        root.Children.Add(officerPanel);

        var caseRootPanel = new Grid { Margin = new Thickness(0, 12, 0, 0) };
        caseRootPanel.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        caseRootPanel.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        var caseRootLabeled = LabeledControl("Zaakmap", _caseRoot);
        caseRootPanel.Children.Add(caseRootLabeled);
        var browse = new System.Windows.Controls.Button
        {
            Content = "Bladeren...",
            MinWidth = 90,
            Margin = new Thickness(10, 22, 0, 0),
        };
        browse.Click += (_, _) => BrowseCaseRoot();
        Grid.SetColumn(browse, 1);
        caseRootPanel.Children.Add(browse);
        Grid.SetRow(caseRootPanel, 2);
        root.Children.Add(caseRootPanel);

        var casesPanel = new Grid { Margin = new Thickness(0, 12, 0, 0) };
        casesPanel.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        casesPanel.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        casesPanel.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        casesPanel.Children.Add(new TextBlock { Text = "Bestaande zaken", Margin = new Thickness(0, 0, 0, 6) });
        Grid.SetRow(_cases, 1);
        casesPanel.Children.Add(_cases);
        _cases.SelectionChanged += (_, _) =>
        {
            if (_cases.SelectedItem is string selected)
            {
                _caseNumber.Text = selected;
            }
        };
        var caseInput = LabeledControl("Zaaknummer", _caseNumber);
        caseInput.Margin = new Thickness(0, 10, 0, 0);
        Grid.SetRow(caseInput, 2);
        casesPanel.Children.Add(caseInput);
        Grid.SetRow(casesPanel, 3);
        root.Children.Add(casesPanel);

        var buttons = new StackPanel
        {
            Orientation = System.Windows.Controls.Orientation.Horizontal,
            HorizontalAlignment = System.Windows.HorizontalAlignment.Right,
            Margin = new Thickness(0, 16, 0, 0),
        };
        var cancel = new System.Windows.Controls.Button { Content = "Annuleren", MinWidth = 90 };
        cancel.Click += (_, _) => DialogResult = false;
        var start = new System.Windows.Controls.Button { Content = "Starten", MinWidth = 90, Margin = new Thickness(10, 0, 0, 0) };
        start.Click += (_, _) => Accept();
        buttons.Children.Add(cancel);
        buttons.Children.Add(start);
        Grid.SetRow(buttons, 4);
        root.Children.Add(buttons);

        Content = root;
        _caseRoot.Text = LoadDefaultCaseRoot();
        RefreshCases();
    }

    /// <summary>
    /// Wraps an input control with a small text label for consistent dialog layout.
    /// </summary>
    private static FrameworkElement LabeledControl(string label, System.Windows.Controls.Control control)
    {
        var panel = new StackPanel();
        panel.Children.Add(new TextBlock { Text = label, Margin = new Thickness(0, 0, 0, 4) });
        control.Height = 32;
        panel.Children.Add(control);
        return panel;
    }

    /// <summary>
    /// Lets the operator choose a different case root and refreshes the case list.
    /// </summary>
    private void BrowseCaseRoot()
    {
        using var dialog = new WinForms.FolderBrowserDialog { SelectedPath = _caseRoot.Text };
        if (dialog.ShowDialog() == WinForms.DialogResult.OK)
        {
            _caseRoot.Text = dialog.SelectedPath;
            RefreshCases();
        }
    }

    /// <summary>
    /// Reloads existing case folders from the selected case root.
    /// </summary>
    private void RefreshCases()
    {
        _cases.Items.Clear();
        if (!Directory.Exists(_caseRoot.Text))
        {
            return;
        }

        foreach (var dir in Directory.EnumerateDirectories(_caseRoot.Text).OrderBy(Path.GetFileName))
        {
            _cases.Items.Add(Path.GetFileName(dir));
        }
    }

    /// <summary>
    /// Validates the dialog fields and stores the selected session values.
    /// </summary>
    private void Accept()
    {
        var officer = _officer.Text.Trim();
        var caseNumber = _caseNumber.Text.Trim();
        var caseRoot = _caseRoot.Text.Trim();
        if (string.IsNullOrWhiteSpace(officer) || string.IsNullOrWhiteSpace(caseNumber) || string.IsNullOrWhiteSpace(caseRoot))
        {
            System.Windows.MessageBox.Show("Vul de naam van de medewerker, het zaaknummer en de zaakmap in.", "Sessie", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        Result = new SessionPromptResult(officer, caseNumber, caseRoot);
        DialogResult = true;
    }

    /// <summary>
    /// Uses the current Windows user's Desktop as the default case root.
    /// </summary>
    private static string LoadDefaultCaseRoot()
    {
        var desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
        return string.IsNullOrWhiteSpace(desktop)
            ? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Desktop")
            : desktop;
    }
}
