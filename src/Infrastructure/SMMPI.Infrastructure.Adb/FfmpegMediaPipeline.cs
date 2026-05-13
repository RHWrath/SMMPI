using System.Globalization;
using SMMPI.Domain.Entities;
using SMMPI.Domain.Enums;
using SMMPI.Domain.Interfaces;

namespace SMMPI.Infrastructure.Adb;

public sealed class FfmpegMediaPipeline : IMediaPipeline
{
    private readonly FfmpegCommandBuilder _builder;
    private readonly FfmpegCommandRunner _runner;

    public FfmpegMediaPipeline()
        : this(new FfmpegCommandBuilder(), new FfmpegCommandRunner())
    {
    }

    public FfmpegMediaPipeline(FfmpegCommandBuilder builder, FfmpegCommandRunner runner)
    {
        _builder = builder;
        _runner = runner;
    }

    public async Task<MediaProcessingResult> PrepareAsync(MediaProcessingRequest request, CancellationToken cancellationToken)
    {
        Directory.CreateDirectory(request.WorkingDirectory);
        var outputPath = Path.Combine(request.WorkingDirectory, request.Profile.OutputFileName);

        try
        {
            var duration = request.Media.Type == MediaType.Video
                ? await GetDurationAsync(request.Media.Path, cancellationToken)
                : request.Profile.ImageLoopDuration;

            if (request.Media.Type == MediaType.Video && duration > request.Profile.MaxVideoDuration)
            {
                return new MediaProcessingResult(
                    false,
                    outputPath,
                    request.Profile.OutputFileName,
                    duration,
                    $"Video is too long ({duration.TotalSeconds:0.0}s). Maximum is {request.Profile.MaxVideoDuration.TotalSeconds:0}s.");
            }

            var command = request.Media.Type == MediaType.Image
                ? _builder.BuildImageLoop(request.Media.Path, outputPath, request.Profile)
                : _builder.BuildVideoConversion(request.Media.Path, outputPath, request.Profile);

            await _runner.RunAsync(command, cancellationToken);

            return new MediaProcessingResult(true, outputPath, request.Profile.OutputFileName, duration, null);
        }
        catch (Exception ex)
        {
            return new MediaProcessingResult(false, outputPath, request.Profile.OutputFileName, null, ex.Message);
        }
    }

    private async Task<TimeSpan> GetDurationAsync(string path, CancellationToken cancellationToken)
    {
        var output = await _runner.RunAsync(_builder.BuildDurationProbe(path), cancellationToken);
        return double.TryParse(output, NumberStyles.Float, CultureInfo.InvariantCulture, out var seconds)
            ? TimeSpan.FromSeconds(seconds)
            : TimeSpan.Zero;
    }
}
