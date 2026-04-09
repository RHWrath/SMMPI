using System.Collections.ObjectModel;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using AdvancedSharpAdbClient.Models;
using WPFTest.Services;

namespace WPFTest;

public partial class MainWindow : Window
{
    private readonly AdbConnectionService _adb = new();
    private readonly List<DeviceData> _devices = new();
    private DeviceData? _connectedDevice;

    public MainWindow()
    {
        InitializeComponent();
        Loaded += (_, _) => OnLoaded();
    }

    private void OnLoaded()
    {
        var bundled = AppPaths.BundledScrcpyServerPath;
        if (!File.Exists(bundled))
        {
            AdbStatusLabel.Text =
                $"Warning: bundled scrcpy-server not found at:\n{bundled}";
            AdbStatusLabel.Foreground = System.Windows.Media.Brushes.DarkRed;
        }

        RefreshDevicesButton_OnClick(this, new RoutedEventArgs());
        UpdateConnectButtonState();
    }

    private void RefreshDevicesButton_OnClick(object sender, RoutedEventArgs e)
    {
        AdbStatusLabel.Foreground = System.Windows.Media.Brushes.DarkOrange;
        var err = _adb.TryEnsureAdbServerStarted();
        if (err is not null)
        {
            AdbStatusLabel.Text = err;
            _devices.Clear();
            DeviceListBox.ItemsSource = null;
            ConnectDeviceButton.IsEnabled = false;
            return;
        }

        _devices.Clear();
        _devices.AddRange(_adb.GetDevices());
        DeviceListBox.ItemsSource = new ObservableCollection<string>(
            _devices.Select(d => _adb.GetDeviceDisplayName(d) ?? d.Serial));

        AdbStatusLabel.Text = _devices.Count == 0
            ? "ADB OK — no devices online. Connect USB and enable debugging."
            : $"ADB OK — {_devices.Count} device(s). Select one and click Use selected device.";

        UpdateConnectButtonState();
    }

    private void DeviceListBox_OnSelectionChanged(object sender, SelectionChangedEventArgs e) =>
        UpdateConnectButtonState();

    private void UpdateConnectButtonState() =>
        ConnectDeviceButton.IsEnabled = DeviceListBox.SelectedIndex >= 0 && _devices.Count > 0;

    private void ConnectDeviceButton_OnClick(object sender, RoutedEventArgs e)
    {
        var i = DeviceListBox.SelectedIndex;
        if (i < 0 || i >= _devices.Count)
        {
            return;
        }

        _connectedDevice = _devices[i];
        InfoLabel.Text = $"Connected: {_adb.GetDeviceDisplayName(_connectedDevice)}";
        StreamPlaceholderLabel.Text = "Ready for scrcpy stream integration.";
        AdbStatusLabel.Foreground = System.Windows.Media.Brushes.DarkGreen;
        AdbStatusLabel.Text = "Device selected. Screen mirror + push will use this device.";
    }
}
