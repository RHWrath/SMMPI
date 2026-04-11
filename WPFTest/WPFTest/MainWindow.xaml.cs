using Layers.Business.Logging;
using Layers.Business.Plugins;
using Layers.Tools;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Navigation;
using System.Windows.Shapes;

namespace WPFTest
{
    /// <summary>
    /// Interaction logic for MainWindow.xaml
    /// </summary>
    /// 

    public partial class MainWindow : Window
    {
        [DllImport("kernel32.dll")]
        static extern bool AllocConsole();
        public MainWindow()
        {
            EnvReader.Load("../../../../.env");

            InitializeComponent();
            AllocConsole();  // Call to open console
            Console.WriteLine("Console opened!");

            ComboBox1.ItemsSource = Enum.GetValues(typeof(LogCategory));
            ComboBox1.SelectedIndex = 0;

            
        }

        private void btnReadLogs_Click(object sender, RoutedEventArgs e)
        {
            
            var target = new TargetData();

            target.Feed(LogCategory.Chat, new ChatLog("Hi from Discord", "user123", DateTime.Now));
            target.Feed(LogCategory.Chat, new ChatLog("Hi my name is Chuck", "user124", DateTime.Now));

            target.Feed(LogCategory.User, new UserLog("user123", "NicolasCage", DateOnly.FromDateTime(DateTime.Now),
                "discord,steam,etc...", DateTime.Now));
            target.Feed(LogCategory.User, new UserLog("user124", "ChuckNorriss", DateOnly.FromDateTime(DateTime.Now),
                "discord,steam,etc...", DateTime.Now));

            target.Feed(LogCategory.Recording, new MediaLog(File.ReadAllBytes("C:\\Users\\neoks\\Videos\\test.mkv"), "video/mkv", DateTime.Now));
            target.Feed(LogCategory.Recording, new MediaLog(File.ReadAllBytes("C:\\Users\\neoks\\Videos\\test.mkv"), "video/mp4", DateTime.Now));
            target.Feed(LogCategory.Recording, new MediaLog(File.ReadAllBytes("C:\\Users\\neoks\\Videos\\test.mkv"), "video/wav", DateTime.Now));
            
            foreach (var log in target.ExtractLogs((LogCategory)ComboBox1.SelectedValue))
                Console.WriteLine(log.ToString());
        }

        private async void btnAuth_Click(object sender, RoutedEventArgs e)
        {
            DiscordPlugin plugin = new DiscordPlugin();
            await plugin.Authenticate();
        }
    }
}