using System;
using System.Collections.Generic;
using System.IO;
using Concentus.Oggfile;
using Concentus.Structs;
using Silk.NET.OpenAL;

namespace DokaponSoFTools.App.Services;

/// <summary>
/// Cross-platform audio output via OpenAL Soft (Silk.NET). Replaces the
/// Windows-only NAudio path. Opus is decoded with Concentus and Ogg Vorbis with
/// NVorbis (both pure C#); the resulting 16-bit PCM is handed to a single
/// OpenAL buffer/source.
///
/// Initialization is lazy and defensive: if the OpenAL native can't be loaded
/// (e.g. headless CI, or a packaging issue), audio simply degrades to silence
/// with a logged warning — it never crashes the app.
/// </summary>
public sealed class OpenAlAudioPlayer : IAudioPlayer
{
    private AL? _al;
    private ALContext? _alc;
    private IntPtr _device;
    private IntPtr _context;
    private uint _source;
    private uint _buffer;
    private bool _triedInit;
    private bool _available;

    private unsafe bool EnsureInitialized()
    {
        if (_triedInit) return _available;
        _triedInit = true;

        try
        {
            // 'true' selects the bundled OpenAL Soft native (Silk.NET.OpenAL.Soft.Native).
            _alc = ALContext.GetApi(true);
            _al = AL.GetApi(true);

            var device = _alc.OpenDevice("");
            if (device == null)
                throw new InvalidOperationException("no output device");

            var context = _alc.CreateContext(device, null);
            _alc.MakeContextCurrent(context);

            _device = (IntPtr)device;
            _context = (IntPtr)context;
            _available = true;
        }
        catch (Exception ex)
        {
            _available = false;
            StatusLogService.Instance.Warning($"Audio playback unavailable: {ex.Message}");
        }

        return _available;
    }

    public unsafe void Play(byte[] data, bool isOpus)
    {
        Stop();
        if (!EnsureInitialized() || _al is null) return;

        var (pcm, channels, rate) = Decode(data, isOpus);
        if (pcm.Length == 0) return;

        _buffer = _al.GenBuffer();
        var format = channels >= 2 ? BufferFormat.Stereo16 : BufferFormat.Mono16;
        _al.BufferData<short>(_buffer, format, pcm, rate);

        _source = _al.GenSource();
        _al.SetSourceProperty(_source, SourceInteger.Buffer, (int)_buffer);
        _al.SourcePlay(_source);
    }

    public void Stop()
    {
        if (_al is null) return;

        if (_source != 0)
        {
            _al.SourceStop(_source);
            _al.SetSourceProperty(_source, SourceInteger.Buffer, 0);
            _al.DeleteSource(_source);
            _source = 0;
        }
        if (_buffer != 0)
        {
            _al.DeleteBuffer(_buffer);
            _buffer = 0;
        }
    }

    public bool IsPlaying
    {
        get
        {
            if (!_available || _al is null || _source == 0) return false;
            _al.GetSourceProperty(_source, GetSourceInteger.SourceState, out int state);
            return state == (int)SourceState.Playing;
        }
    }

    private static (short[] pcm, int channels, int rate) Decode(byte[] data, bool isOpus)
    {
        if (isOpus)
        {
            using var ms = new MemoryStream(data);
#pragma warning disable CS0618 // matches the shipped decode path; OpusOggReadStream takes this decoder
            var decoder = new OpusDecoder(48000, 2);
#pragma warning restore CS0618
            var reader = new OpusOggReadStream(decoder, ms);
            var samples = new List<short>();
            while (reader.HasNextPacket)
            {
                short[]? packet = reader.DecodeNextPacket();
                if (packet is not null) samples.AddRange(packet);
            }
            return (samples.ToArray(), 2, 48000);
        }
        else
        {
            using var ms = new MemoryStream(data);
            using var vorbis = new NVorbis.VorbisReader(ms, closeOnDispose: false);
            int channels = vorbis.Channels;
            int rate = vorbis.SampleRate;

            var floatBuf = new float[channels * 8192];
            var samples = new List<short>();
            int read;
            while ((read = vorbis.ReadSamples(floatBuf, 0, floatBuf.Length)) > 0)
            {
                for (int i = 0; i < read; i++)
                {
                    float f = Math.Clamp(floatBuf[i], -1f, 1f);
                    samples.Add((short)(f * short.MaxValue));
                }
            }
            return (samples.ToArray(), channels, rate);
        }
    }

    public unsafe void Dispose()
    {
        Stop();
        if (_available && _alc is not null)
        {
            _alc.MakeContextCurrent(null);
            if (_context != IntPtr.Zero) _alc.DestroyContext((Context*)_context);
            if (_device != IntPtr.Zero) _alc.CloseDevice((Device*)_device);
            _available = false;
        }
    }
}
