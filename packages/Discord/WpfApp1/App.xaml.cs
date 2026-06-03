using System.Configuration;
using System.Data;
using System.Runtime.InteropServices;
using System.Windows;

namespace WpfApp1;

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
    }
}

