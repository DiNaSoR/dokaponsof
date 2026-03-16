using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using Concentus.Structs;
using Concentus.Oggfile;
using DokaponSoFTools.App.Services;
using DokaponSoFTools.App.ViewModels;
using NAudio.Wave;

namespace DokaponSoFTools.App.Views;

public partial class VoiceToolsView : UserControl
{
    private WaveOutEvent? _waveOut;
    private IWaveProvider? _waveProvider;

    public VoiceToolsView()
    {
        InitializeComponent();
        Unloaded += (_, _) => StopAndCleanup();
    }

    private void SoundsGrid_MouseDoubleClick(object sender, MouseButtonEventArgs e)
    {
        if (sender is DataGrid grid && grid.SelectedItem is SoundItem item && DataContext is VoiceToolsViewModel vm)
            PlaySound(item, vm);
    }

    private void BtnPlay_Click(object sender, RoutedEventArgs e)
    {
        if (_waveOut?.PlaybackState == PlaybackState.Paused)
        {
            _waveOut.Play();
            return;
        }

        // Find selected sound from the active tab's grid
        SoundItem? item = null;
        if (DataContext is VoiceToolsViewModel vm)
        {
            item = vm.SelectedSound;
            if (item is not null) PlaySound(item, vm);
        }
    }

    private void BtnStop_Click(object sender, RoutedEventArgs e) => StopAndCleanup();

    private void PlaySound(SoundItem item, VoiceToolsViewModel vm)
    {
        StopAndCleanup();

        try
        {
            var archive = vm.CurrentArchive;
            if (archive is null) return;

            var sound = archive.Sounds.FirstOrDefault(s => s.Name == item.Name);
            if (sound is null) return;

            if (sound.IsOpus)
            {
                // Decode Ogg Opus to PCM using Concentus
                using var oggStream = new MemoryStream(sound.Data);
                var opusDecoder = new OpusDecoder(48000, 2);
                var oggReader = new OpusOggReadStream(opusDecoder, oggStream);

                var pcmSamples = new List<short>();
                while (oggReader.HasNextPacket)
                {
                    short[]? packet = oggReader.DecodeNextPacket();
                    if (packet is not null)
                        pcmSamples.AddRange(packet);
                }

                byte[] pcmBytes = new byte[pcmSamples.Count * 2];
                for (int i = 0; i < pcmSamples.Count; i++)
                {
                    pcmBytes[i * 2] = (byte)(pcmSamples[i] & 0xFF);
                    pcmBytes[i * 2 + 1] = (byte)((pcmSamples[i] >> 8) & 0xFF);
                }

                var waveFormat = new WaveFormat(48000, 16, 2);
                var ms = new MemoryStream(pcmBytes);
                _waveProvider = new RawSourceWaveStream(ms, waveFormat);
            }
            else
            {
                var tempFile = Path.Combine(Path.GetTempPath(), $"dokapon_{Guid.NewGuid():N}.ogg");
                File.WriteAllBytes(tempFile, sound.Data);
                _waveProvider = new NAudio.Vorbis.VorbisWaveReader(tempFile);
            }

            _waveOut = new WaveOutEvent();
            _waveOut.Init(_waveProvider);
            _waveOut.PlaybackStopped += (_, _) =>
                Dispatcher.Invoke(() => nowPlayingText.Text = "");
            _waveOut.Play();
            nowPlayingText.Text = $"Playing: {item.Name}";
        }
        catch (Exception ex)
        {
            StatusLogService.Instance.Warning($"Playback failed: {ex.Message}");
            StopAndCleanup();
        }
    }

    private void StopAndCleanup()
    {
        try { _waveOut?.Stop(); } catch { }
        _waveOut?.Dispose();
        _waveOut = null;

        if (_waveProvider is IDisposable d) d.Dispose();
        _waveProvider = null;

        nowPlayingText.Text = "";
    }
}
