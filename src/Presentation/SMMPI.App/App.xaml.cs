using SMMPI.Infrastructure.Plugins.Tools;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows;

namespace WPFTest;

/// <summary>
/// Interaction logic for App.xaml
/// </summary>
public partial class App : Application
{
    [DllImport("kernel32.dll")]
    static extern bool AllocConsole();
    protected override async void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        AllocConsole();  // Call to open console
        Console.WriteLine("Console opened!");

        try
        {
            string slnRoot = SolutionRoot.Get();
            string packageDir = Path.Combine(slnRoot, "./packages/old/Project/VCAM_GUI-master(3)/VCAM_GUI-master/");
            string dependencyPath = Path.Combine(packageDir, "requirements.txt");

            if (!File.Exists(dependencyPath))
            {
                throw new FileNotFoundException($"Python dependencies not found: {dependencyPath}");
            }

            await EnsurePipAsync(packageDir);
            await InstallRequirementsAsync(packageDir);

            var window = new MainWindow();
            window.Show();
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                $"Startup failed:\n{ex.Message}",
                "Startup error",
                MessageBoxButton.OK,
                MessageBoxImage.Error);

            Shutdown();
        }
    }

    private static async Task EnsurePipAsync(string workingDir)
    {
        Console.WriteLine("Checking whether pip is available...");

        bool hasPip = await ProcessHandler.TryRunProcessAsync(
            "python",
            "-m pip --version",
            workingDir);

        if (hasPip)
        {
            Console.WriteLine("pip is already installed.");
            return;
        }

        Console.WriteLine("pip not found. Running ensurepip...");
        await ProcessHandler.RunProcessCheckedAsync(
            "python",
            "-m ensurepip --upgrade",
            workingDir);
    }

    private static async Task InstallRequirementsAsync(string dependencyPath)
    {
        Console.WriteLine("Installing dependencies");
        await ProcessHandler.RunProcessCheckedAsync(
            "python",
            "-m pip install -r requirements.txt",
            dependencyPath);
    }
}