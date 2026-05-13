namespace SMMPI.Infrastructure.Adb;

/// <summary>Lets the UI pause heavy capture while the operator drags on the preview (PNG path only; H.264 path is a no-op).</summary>
public interface IStreamTouchInteractionPause
{
    void PushInteractionPause();

    void PopInteractionPause();
}
