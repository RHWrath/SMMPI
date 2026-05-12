namespace SMMPI.Domain.Entities;

public sealed record MediaProcessingRequest(MediaItem Media, DeviceProfile Profile, string WorkingDirectory)
{
    public string SourcePath => Media.Path;
}
