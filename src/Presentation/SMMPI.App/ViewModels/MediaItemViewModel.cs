using System.Windows.Media;

namespace SMMPI.App.ViewModels;

/// <summary>
/// Presentation model for one media item in the explorer grid.
/// </summary>
public sealed class MediaItemViewModel : ObservableObject
{
    private ImageSource? _thumbnail;

    /// <summary>
    /// Creates a view model for the supplied media item.
    /// </summary>
    public MediaItemViewModel(AppMediaItem media)
    {
        Media = media;
    }

    public AppMediaItem Media { get; }

    public string FileName => Media.FileName;

    public string Type => Media.Type == AppMediaType.Video ? "video" : "afbeelding";

    public ImageSource? Thumbnail
    {
        get => _thumbnail;
        set => SetProperty(ref _thumbnail, value);
    }
}
