namespace SMMPI.Domain.Entities;

public class AndroidDevice
{
    public string Serial { get; init; } = string.Empty;
    public string State { get; init; } = string.Empty;
    public string DisplayName => $"{Serial} ({State})";
}
