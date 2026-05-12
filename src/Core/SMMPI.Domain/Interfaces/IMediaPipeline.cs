using SMMPI.Domain.Entities;

namespace SMMPI.Domain.Interfaces;

public interface IMediaPipeline
{
    Task<MediaProcessingResult> PrepareAsync(MediaProcessingRequest request, CancellationToken cancellationToken);
}
