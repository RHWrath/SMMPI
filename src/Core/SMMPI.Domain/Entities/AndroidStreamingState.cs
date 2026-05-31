namespace SMMPI.Domain.Entities;

public sealed record AndroidStreamingState(
    bool IsRunning,
    bool IsRecording,
    int? ProcessId,
    string? WindowTitle,
    string? WarningMessage);
