using SMMPI.Domain.Entities;
using SMMPI.Domain.Enums;

namespace SMMPI.Infrastructure.Adb;

public sealed class FfmpegCommandBuilder
{
    private readonly string _ffmpegPath;
    private readonly string _ffprobePath;

    public FfmpegCommandBuilder()
        : this(FfmpegLocator.Resolve(), FfmpegLocator.ResolveFfprobe())
    {
    }

    public FfmpegCommandBuilder(string ffmpegPath, string ffprobePath)
    {
        _ffmpegPath = ffmpegPath;
        _ffprobePath = ffprobePath;
    }

    public FfmpegCommand BuildVideoConversion(string sourcePath, string outputPath, DeviceProfile profile)
    {
        var filter = BuildScaleFilter(profile, usePadding: false);
        var arguments =
            $"-i {Quote(sourcePath)} -vf {Quote(filter)} -c:v libx264 -preset medium -crf 23 " +
            $"-c:a aac -b:a 128k -pix_fmt yuv420p -movflags +faststart -y {Quote(outputPath)}";

        return new FfmpegCommand(_ffmpegPath, arguments);
    }

    public FfmpegCommand BuildImageLoop(string sourcePath, string outputPath, DeviceProfile profile)
    {
        var filter = BuildScaleFilter(profile, usePadding: true);
        var duration = (int)profile.ImageLoopDuration.TotalSeconds;
        var arguments =
            $"-loop 1 -i {Quote(sourcePath)} -c:v libx264 -t {duration} -vf {Quote(filter)} " +
            $"-pix_fmt yuv420p -y {Quote(outputPath)}";

        return new FfmpegCommand(_ffmpegPath, arguments);
    }

    public FfmpegCommand BuildDurationProbe(string sourcePath) =>
        new(_ffprobePath, $"-v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {Quote(sourcePath)}");

    private static string BuildScaleFilter(DeviceProfile profile, bool usePadding)
    {
        var width = profile.TargetWidth;
        var height = profile.TargetHeight;
        var filters = new List<string>();

        if (profile.Transform == MediaTransform.RotateMinus90AndMirror)
        {
            filters.Add("transpose=2");
            filters.Add("hflip");
            width = profile.TargetHeight;
            height = profile.TargetWidth;
        }

        if (usePadding)
        {
            filters.Add($"scale={width}:{height}:force_original_aspect_ratio=decrease");
            filters.Add($"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black");
        }
        else
        {
            filters.Add($"scale={width}:{height}:force_original_aspect_ratio=increase");
            filters.Add($"crop={width}:{height}");
        }

        filters.Add($"fps={profile.FramesPerSecond}");

        return string.Join(',', filters);
    }

    private static string Quote(string value) =>
        value.StartsWith('"') && value.EndsWith('"') ? value : $"\"{value}\"";
}
