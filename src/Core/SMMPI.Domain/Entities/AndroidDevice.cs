using SMMPI.Domain.Enums;

namespace SMMPI.Domain.Entities;

public sealed record AndroidDevice(
    string Serial,
    string Manufacturer,
    string Model,
    string AndroidVersion,
    DeviceConnectionState State)
{
    public string DisplayName => string.IsNullOrWhiteSpace(Manufacturer)
        ? $"{Model} ({Serial})"
        : $"{Manufacturer} {Model} ({Serial})";
}
