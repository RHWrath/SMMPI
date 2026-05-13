using System.Text;

namespace SMMPI.Infrastructure.Adb;

/// <summary>
/// Encodes text for <c>adb shell input text …</c> (Android <c>%s</c> / <c>%n</c> / <c>%%</c> rules plus minimal shell metacharacter backslash escaping).
/// </summary>
public static class AndroidInputTextEncoder
{
    private static ReadOnlySpan<char> ShellMetacharacters => "()&|;<>\"'`$".AsSpan();

    /// <summary>Yields non-empty encoded segments suitable as the last argument to <c>adb … shell input text SEGMENT</c>.</summary>
    public static IEnumerable<string> EncodeToChunks(string? text, int maxChunkLength = 200)
    {
        if (string.IsNullOrEmpty(text))
        {
            yield break;
        }

        maxChunkLength = Math.Clamp(maxChunkLength, 32, 400);
        var buffer = new StringBuilder();
        foreach (var rune in text.EnumerateRunes())
        {
            var segment = EncodeRuneToSegment(rune);
            if (segment.Length == 0)
            {
                continue;
            }

            if (buffer.Length + segment.Length > maxChunkLength && buffer.Length > 0)
            {
                yield return buffer.ToString();
                buffer.Clear();
            }

            buffer.Append(segment);
        }

        if (buffer.Length > 0)
        {
            yield return buffer.ToString();
        }
    }

    private static string EncodeRuneToSegment(Rune rune)
    {
        if (rune.Value == '\r')
        {
            return string.Empty;
        }

        if (rune.Value == '\n')
        {
            return "%n";
        }

        if (rune.Value == '\t')
        {
            return string.Empty;
        }

        if (rune.Value == ' ')
        {
            return "%s";
        }

        if (rune.Value == '%')
        {
            return "%%";
        }

        if (rune.Value == '\\')
        {
            return "\\\\";
        }

        if (rune.Value < 32 || rune.Value == 127)
        {
            return string.Empty;
        }

        Span<char> utf16 = stackalloc char[2];
        var written = rune.EncodeToUtf16(utf16);
        var sb = new StringBuilder(written * 2 + 2);
        for (var i = 0; i < written; i++)
        {
            var c = utf16[i];
            if (ShellMetacharacters.Contains(c))
            {
                sb.Append('\\');
            }

            sb.Append(c);
        }

        return sb.ToString();
    }
}
