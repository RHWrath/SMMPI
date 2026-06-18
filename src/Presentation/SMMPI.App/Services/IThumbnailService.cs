using System.Windows.Media;
using SMMPI.App.ViewModels;

namespace SMMPI.App.Services;

/// <summary>
/// Creates thumbnails and previews for media items shown in the WPF shell.
/// </summary>
public interface IThumbnailService
{
    Task<ImageSource?> CreateThumbnailAsync(AppMediaItem item, CancellationToken cancellationToken);

    Task<ImageSource?> CreatePreviewAsync(AppMediaItem item, CancellationToken cancellationToken);
}
