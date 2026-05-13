namespace SMMPI.Domain.Entities;

public sealed record StreamFrame(byte[] ImageBytes, int Width, int Height, DateTimeOffset CapturedAt, StreamFrameFormat Format = StreamFrameFormat.Png);
