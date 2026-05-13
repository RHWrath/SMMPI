using SMMPI.Domain.Enums;

namespace SMMPI.Domain.Entities;

public sealed record MediaItem(string Path, MediaType Type)
{
    public string FileName => System.IO.Path.GetFileName(Path);
}
