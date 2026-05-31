namespace SMMPI.Domain.Entities;

public sealed record AndroidStreamingOptions(
    bool AudioEnabled = true,
    int MaxFramesPerSecond = 30,
    int MaxSize = 1280,
    string? RecordPath = null,
    string? WindowTitle = null);
