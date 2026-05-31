using SMMPI.Domain.Entities;

namespace SMMPI.Domain.Interfaces;

public interface IPlatformDetectionService
{
    Task<PlatformTarget?> GetActivePlatformAsync(string serial, CancellationToken cancellationToken);
}
