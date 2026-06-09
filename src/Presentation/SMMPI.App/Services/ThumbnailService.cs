using System.Diagnostics;
using System.IO;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using SMMPI.App.ViewModels;
using SMMPI.Infrastructure.Adb;

namespace SMMPI.App.Services;

/// <summary>
/// Creates still-image thumbnails for the media explorer and decodes stream frames for display.
/// </summary>
public sealed class ThumbnailService : IThumbnailService
{
    /// <summary>
    /// Creates a thumbnail for an image or extracts a representative frame for a video.
    /// </summary>
    public async Task<ImageSource?> CreateThumbnailAsync(AppMediaItem item, CancellationToken cancellationToken)
    {
        var path = item.Type == AppMediaType.Video
            ? await ExtractVideoFrameAsync(item.Path, cancellationToken)
            : item.Path;

        if (path is null || !File.Exists(path))
        {
            return null;
        }

        return LoadImage(path, decodeMaxWidth: 320);
    }

    /// <summary>
    /// Creates a larger preview image for the selected media item without reusing the small explorer thumbnail.
    /// </summary>
    public async Task<ImageSource?> CreatePreviewAsync(AppMediaItem item, CancellationToken cancellationToken)
    {
        var path = item.Type == AppMediaType.Video
            ? await ExtractVideoFrameAsync(item.Path, cancellationToken)
            : item.Path;

        if (path is null || !File.Exists(path))
        {
            return null;
        }

        return LoadImage(path, decodeMaxWidth: 1400);
    }

    /// <summary>
    /// Loads an image file into a frozen WPF image source suitable for binding.
    /// </summary>
    public static ImageSource? LoadImage(string path, int? decodeMaxWidth = null)
    {
        var image = new BitmapImage();
        image.BeginInit();
        image.CacheOption = BitmapCacheOption.OnLoad;
        image.UriSource = new Uri(path);
        if (decodeMaxWidth is > 0)
        {
            image.DecodePixelWidth = decodeMaxWidth.Value;
        }

        image.EndInit();
        image.Freeze();
        return image;
    }

    /// <summary>
    /// Loads PNG bytes into a frozen WPF image source.
    /// </summary>
    public static ImageSource LoadImage(byte[] bytes) => LoadPngBytes(bytes, decodeMaxWidth: null);

    /// <summary>
    /// Decode PNG from memory. When <paramref name="decodeMaxWidth"/> is set, decodes at that max width for faster UI (stream preview).
    /// </summary>
    public static ImageSource LoadPngBytes(byte[] bytes, int? decodeMaxWidth)
    {
        using var stream = new MemoryStream(bytes, writable: false);
        var image = new BitmapImage();
        image.BeginInit();
        image.CreateOptions = BitmapCreateOptions.IgnoreColorProfile;
        image.CacheOption = BitmapCacheOption.OnLoad;
        image.StreamSource = stream;
        if (decodeMaxWidth is > 0)
        {
            image.DecodePixelWidth = decodeMaxWidth.Value;
        }

        image.EndInit();
        image.Freeze();
        return image;
    }

    /// <summary>Decode JPEG from memory (stream / MJPEG frames).</summary>
    public static ImageSource LoadJpegBytes(byte[] bytes, int? decodeMaxWidth)
    {
        using var stream = new MemoryStream(bytes, writable: false);
        var image = new BitmapImage();
        image.BeginInit();
        image.CreateOptions = BitmapCreateOptions.IgnoreColorProfile;
        image.CacheOption = BitmapCacheOption.OnLoad;
        image.StreamSource = stream;
        if (decodeMaxWidth is > 0)
        {
            image.DecodePixelWidth = decodeMaxWidth.Value;
        }

        image.EndInit();
        image.Freeze();
        return image;
    }

    /// <summary>
    /// Uses FFmpeg to extract a thumbnail frame from a video file.
    /// </summary>
    private async Task<string?> ExtractVideoFrameAsync(string path, CancellationToken cancellationToken)
    {
        var output = Path.Combine(Path.GetTempPath(), "SMMPI", "thumbs", $"{Guid.NewGuid():N}.jpg");
        Directory.CreateDirectory(Path.GetDirectoryName(output)!);
        var ffmpeg = ResolveFfmpegPath();

        try
        {
            using var process = Process.Start(new ProcessStartInfo
            {
                FileName = ffmpeg,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
                ArgumentList =
                {
                    "-ss",
                    "00:00:01",
                    "-i",
                    path,
                    "-frames:v",
                    "1",
                    "-q:v",
                    "2",
                    "-y",
                    output,
                },
            });

            if (process is null)
            {
                return null;
            }

            await process.WaitForExitAsync(cancellationToken);
            if (process.ExitCode != 0)
            {
                return null;
            }

            return output;
        }
        catch
        {
            return null;
        }
    }

    /// <summary>
    /// Finds the bundled FFmpeg executable, falling back to the system PATH.
    /// </summary>
    private static string ResolveFfmpegPath()
    {
        try
        {
            return FfmpegLocator.Resolve();
        }
        catch (FileNotFoundException)
        {
            return "ffmpeg";
        }
    }
}
