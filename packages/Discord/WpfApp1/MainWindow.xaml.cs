using Microsoft.Win32;
using SMMPI.Infrastructure.Plugins.Tools;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Shapes;

namespace WpfApp1
{
    /// <summary>
    /// Interaction logic for MainWindow.xaml
    /// </summary>
    /// 
    public class InvalidJsonFileException : Exception
    {
        public InvalidJsonFileException(string message) : base(message) { }
    }
    public partial class MainWindow : Window
    {
        string slnRoot;
        string packageDir;
        string exePath;
        string outputdir;
        string token;
        string serverid;
        string channel;
        string formattedAfterDate;
        string formattedBeforeDate;
        string jsonFilePath;

        public MainWindow()
        {
            InitializeComponent();
            slnRoot = SolutionRoot.Get();
            packageDir = System.IO.Path.Combine(slnRoot, "Packages", "DiscordChatExporter");
            outputdir = System.IO.Path.Combine(slnRoot, "Output");
            exePath = System.IO.Path.Combine(packageDir, "DiscordChatExporter.Cli.exe");

            cbbFormat.ItemsSource = new string[] { "PlainText", "HtmlDark", "HtmlLight", "Csv", "Json" };
            txtConsole.Text += "\n";
            formattedAfterDate = dtpAfterTime.SelectedDate.Value.ToString("MM/dd/yyyy");
            formattedBeforeDate = dtpBeforeTime.SelectedDate.Value.ToString("MM/dd/yyyy");
        }

        private void AppendConsole(string text)
        {
            Dispatcher.Invoke(() =>
            {
                txtConsole.AppendText(text + Environment.NewLine);
                txtConsole.ScrollToEnd();
            });
        }


        private void toggleVisibility()
        {

            ExportGroup.Visibility = ExportGroup.Visibility == Visibility.Visible ? ExportGroup.Visibility = Visibility.Hidden : ExportGroup.Visibility = Visibility.Visible;
        }

        private async void btnDms(object sender, RoutedEventArgs e)
        {
            txtConsole.Clear();
            try
            {
                await ProcessHandler.RunProcessCheckedAsync(
                    exePath,
                    $"dm -t {token}",
                    packageDir,
                    AppendConsole
                );
            }
            catch (Exception ex)
            {
                AppendConsole("[exception] " + ex.Message);
            }
        }

        private async void btnChannels(object sender, RoutedEventArgs e)
        {
            txtConsole.Clear();
            try
            {
                await ProcessHandler.RunProcessCheckedAsync(
                    exePath,
                    $"channels -g {serverid} -t {token}",
                    packageDir,
                    AppendConsole
                );
            }
            catch (Exception ex)
            {
                AppendConsole("[exception] " + ex.Message);
            }
        }
        private async void btnExport(object sender, RoutedEventArgs e)
        {
            txtConsole.Clear();
            try
            {
                string format = cbbFormat.SelectedValue.ToString();
                string jsonInputDir = "";

                if(format == "Json")
                {
                    jsonInputDir = "\\jsonInput\\" + DateTime.Now.ToString("dd-MM-yyyy_HH-mm");
                    SolutionRoot.checkDirectoryExistsAndCreate(outputdir + jsonInputDir);
                }
                
                await ProcessHandler.RunProcessCheckedAsync(
                    exePath,
                    $"{(chkExportAll.IsChecked == true ? "exportall" : "export")} -t {token} -f {format} -c {channel} " +
                    $"-o {(format == "Json" ? outputdir + jsonInputDir : outputdir)} " +
                    $"--before {formattedBeforeDate} --after {formattedAfterDate}",
                    packageDir,
                    AppendConsole
                );
            }
            catch (Exception ex)
            {
                AppendConsole("[exception] " + ex.Message);
            }
        }

        private void txtToken_TextChanged(object sender, System.Windows.Controls.TextChangedEventArgs e)
        {
            token = txtToken.Text;
        }

        private async void btnOutput(object sender, RoutedEventArgs e)
        {
            await ProcessHandler.TryRunProcessAsync("explorer.exe", outputdir, slnRoot);
        }

        private void btnAuth(object sender, RoutedEventArgs e)
        {
            toggleVisibility();
        }

        private void txtChannel_TextChanged(object sender, System.Windows.Controls.TextChangedEventArgs e)
        {
            channel = txtChannel.Text;
        }

        private void txtServer_TextChanged(object sender, System.Windows.Controls.TextChangedEventArgs e)
        {
            serverid = txtServer.Text;
        }

        private void DtpAfterTime_SelectedDateChanged(object sender, SelectionChangedEventArgs e)
        {
            DatePicker dp = (DatePicker)sender;

            if (dp.SelectedDate.HasValue)
            {
                formattedAfterDate = dp.SelectedDate.Value.ToString("MM/dd/yyyy");
            }
        }
        private void DtpBeforeTime_SelectedDateChanged(object sender, SelectionChangedEventArgs e)
        {
            DatePicker dp = (DatePicker)sender;

            if (dp.SelectedDate.HasValue)
            {
                formattedBeforeDate = dp.SelectedDate.Value.ToString("MM/dd/yyyy");
            }
        }
        private async void btnParseJSON_Clicked(object sender, RoutedEventArgs e)
        {

            if(jsonFilePath == null)
            {
                MessageBox.Show(
                    "No file has been selected.",
                    "Invalid JSON",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);

                return;
            }

            await JSONParser.ParseJSON(jsonFilePath);
        }

        private void btnChooseFile_Clicked(object sender, RoutedEventArgs e)
        {
            try
            {
                OpenFileDialog openFileDialog = new OpenFileDialog
                {
                    Title = "Choose a JSON file",
                    Filter = "JSON files (*.json)|*.json|All files (*.*)|*.*",
                    FilterIndex = 1,
                    Multiselect = false,
                    InitialDirectory = outputdir
                };

                bool? result = openFileDialog.ShowDialog();

                if (result != true)
                    return;

                string selectedPath = openFileDialog.FileName;

                if (!string.Equals(System.IO.Path.GetExtension(selectedPath), ".json", StringComparison.OrdinalIgnoreCase))
                {
                    throw new InvalidJsonFileException("The selected file must have a .json extension.");
                }

                string json = File.ReadAllText(selectedPath);
                JsonDocument.Parse(json);

                jsonFilePath = selectedPath;
                btnChooseFile.Content = System.IO.Path.GetFileName(jsonFilePath);

                MessageBox.Show(
                    "JSON file selected successfully.",
                    "Success",
                    MessageBoxButton.OK,
                    MessageBoxImage.Information);
            }
            catch (InvalidJsonFileException ex)
            {
                MessageBox.Show(
                    ex.Message,
                    "Invalid file",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
            }
            catch (JsonException)
            {
                MessageBox.Show(
                    "The selected file does not contain valid JSON.",
                    "Invalid JSON",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    $"An unexpected error occurred:\n{ex.Message}",
                    "Error",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
            }
        }
    }
}