namespace SMMPI.Domain.Entities;

public sealed record PlatformTarget(
    string Name,
    string PackageName,
    DeviceProfile Profile);
