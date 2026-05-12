using SMMPI.Domain.Entities;

namespace SMMPI.Infrastructure.Adb;

public static class TouchMapper
{
    public static TouchPoint? MapToDevice(
        double controlWidth,
        double controlHeight,
        int frameWidth,
        int frameHeight,
        int deviceWidth,
        int deviceHeight,
        double controlX,
        double controlY)
    {
        if (controlWidth <= 0 || controlHeight <= 0 || frameWidth <= 0 || frameHeight <= 0)
        {
            return null;
        }

        var scale = Math.Min(controlWidth / frameWidth, controlHeight / frameHeight);
        var renderedWidth = frameWidth * scale;
        var renderedHeight = frameHeight * scale;
        var offsetX = (controlWidth - renderedWidth) / 2;
        var offsetY = (controlHeight - renderedHeight) / 2;

        if (controlX < offsetX || controlX > offsetX + renderedWidth ||
            controlY < offsetY || controlY > offsetY + renderedHeight)
        {
            return null;
        }

        var frameX = (controlX - offsetX) / scale;
        var frameY = (controlY - offsetY) / scale;

        var deviceX = Clamp((int)Math.Round(frameX * deviceWidth / frameWidth), 0, deviceWidth - 1);
        var deviceY = Clamp((int)Math.Round(frameY * deviceHeight / frameHeight), 0, deviceHeight - 1);

        return new TouchPoint(deviceX, deviceY);
    }

    private static int Clamp(int value, int min, int max) => Math.Min(Math.Max(value, min), max);
}
