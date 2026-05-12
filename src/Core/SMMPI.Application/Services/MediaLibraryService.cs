using SMMPI.Domain.Entities;
using SMMPI.Domain.Enums;
using SMMPI.Domain.Interfaces;

namespace SMMPI.Application.Services;

public sealed class MediaLibraryService : IMediaLibraryService
{
    private static readonly HashSet<string> ImageExtensions = new(StringComparer.OrdinalIgnoreCase)
    {
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"
    };

    private static readonly HashSet<string> VideoExtensions = new(StringComparer.OrdinalIgnoreCase)
    {
        ".mp4", ".mov", ".avi", ".wmv", ".flv", ".webm", ".mkv", ".m4v"
    };

    public IEnumerable<MediaItem> ScanFolder(string folderPath)
    {
        if (string.IsNullOrWhiteSpace(folderPath) || !Directory.Exists(folderPath))
        {
            return [];
        }

        return Directory.EnumerateFiles(folderPath)
            .Select(CreateMediaItem)
            .Where(item => item is not null)
            .Select(item => item!);
    }

    private static MediaItem? CreateMediaItem(string path)
    {
        var extension = Path.GetExtension(path);

        if (ImageExtensions.Contains(extension))
        {
            return new MediaItem(path, MediaType.Image);
        }

        if (VideoExtensions.Contains(extension))
        {
            return new MediaItem(path, MediaType.Video);
        }

        return null;
    }
}
