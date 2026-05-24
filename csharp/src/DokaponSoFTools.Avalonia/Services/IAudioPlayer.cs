using System;

namespace DokaponSoFTools.App.Services;

/// <summary>Cross-platform audio playback for PCK sounds.</summary>
public interface IAudioPlayer : IDisposable
{
    /// <summary>Decode and play a sound. <paramref name="isOpus"/> selects the
    /// Opus (Concentus) or Vorbis (NVorbis) decoder.</summary>
    void Play(byte[] data, bool isOpus);

    void Stop();

    bool IsPlaying { get; }
}
