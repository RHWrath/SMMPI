using SMMPI.Domain.Entities;

namespace SMMPI.Domain.Interfaces;

public interface IMediaLibraryService
{
    IEnumerable<MediaItem> ScanFolder(string folderPath);
}
