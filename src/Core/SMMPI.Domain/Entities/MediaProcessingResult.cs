namespace SMMPI.Domain.Entities;

public sealed record MediaProcessingResult(
    bool Success,
    string OutputPath,
    string OutputFileName,
    TimeSpan? Duration,
    string? ErrorMessage);
