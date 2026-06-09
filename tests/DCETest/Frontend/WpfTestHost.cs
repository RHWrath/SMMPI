using System.Windows;

namespace Teststraat.Frontend;

/// <summary>
/// Ensures a WPF application instance exists for view model tests that touch the dispatcher.
/// </summary>
internal static class WpfTestHost
{
    private static readonly object Gate = new();

    public static void EnsureApplication()
    {
        if (Application.Current is not null)
        {
            return;
        }

        lock (Gate)
        {
            if (Application.Current is not null)
            {
                return;
            }

            new Application();
        }
    }
}
