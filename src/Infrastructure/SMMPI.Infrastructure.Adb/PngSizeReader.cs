namespace SMMPI.Infrastructure.Adb;

public static class PngSizeReader
{
    public static (int Width, int Height) Read(byte[] png)
    {
        if (png.Length < 24)
        {
            return (0, 0);
        }

        var width = ReadBigEndianInt32(png, 16);
        var height = ReadBigEndianInt32(png, 20);
        return (width, height);
    }

    private static int ReadBigEndianInt32(byte[] bytes, int offset) =>
        (bytes[offset] << 24) |
        (bytes[offset + 1] << 16) |
        (bytes[offset + 2] << 8) |
        bytes[offset + 3];
}
