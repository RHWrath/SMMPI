using SMMPI.Domain.Entities;

namespace SMMPI.Infrastructure.Adb;

public sealed class ScrcpyCommandBuilder
{
    public IReadOnlyList<string> BuildArguments(string serial, AndroidStreamingOptions options, bool includeAudio)
    {
        var args = new List<string>
        {
            "--serial",
            serial,
            "--max-fps",
            options.MaxFramesPerSecond.ToString(System.Globalization.CultureInfo.InvariantCulture),
            "--max-size",
            options.MaxSize.ToString(System.Globalization.CultureInfo.InvariantCulture),
        };

        if (!string.IsNullOrWhiteSpace(options.WindowTitle))
        {
            args.Add("--window-title");
            args.Add(options.WindowTitle);
        }

        if (!includeAudio)
        {
            args.Add("--no-audio");
        }
        else if (!string.IsNullOrWhiteSpace(options.RecordPath))
        {
            args.Add("--audio-codec=aac");
        }

        if (!string.IsNullOrWhiteSpace(options.RecordPath))
        {
            args.Add($"--record={options.RecordPath}");
            args.Add("--record-format=mp4");
        }

        return args;
    }
}
