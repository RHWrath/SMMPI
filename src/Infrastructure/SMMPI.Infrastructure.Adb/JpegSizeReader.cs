namespace SMMPI.Infrastructure.Adb;

/// <summary>Reads width/height from baseline / progressive JPEG SOF markers.</summary>
public static class JpegSizeReader
{
    public static (int Width, int Height) Read(byte[] jpeg) => Read(jpeg.AsSpan());

    public static (int Width, int Height) Read(ReadOnlySpan<byte> jpeg)
    {
        for (var i = 0; i < jpeg.Length - 9; i++)
        {
            if (jpeg[i] != 0xFF)
            {
                continue;
            }

            var marker = jpeg[i + 1];
            if (marker is 0xC0 or 0xC1 or 0xC2)
            {
                var h = (jpeg[i + 5] << 8) | jpeg[i + 6];
                var w = (jpeg[i + 7] << 8) | jpeg[i + 8];
                return (w, h);
            }
        }

        return (0, 0);
    }
}
