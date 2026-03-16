using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using DokaponSoFTools.App.Services;
using DokaponSoFTools.App.ViewModels;
using NAudio.Vorbis;
using NAudio.Wave;

namespace DokaponSoFTools.App.Views;

public partial class VoiceToolsView : UserControl
{
    private WaveOutEvent? _waveOut;
    private VorbisWaveReader? _vorbisReader;
    private string? _tempFile;

    public VoiceToolsView()
    {
        InitializeComponent();
        Unloaded += (_, _) => StopAndCleanup();
    }

    private void SoundsGrid_MouseDoubleClick(object sender, MouseButtonEventArgs e)
    {
        if (soundsGrid.SelectedItem is SoundItem item && DataContext is VoiceToolsViewModel vm)
        {
            PlaySound(item, vm);
        }
    }

    private void BtnPlay_Click(object sender, RoutedEventArgs e)
    {
        if (_waveOut?.PlaybackState == PlaybackState.Paused)
        {
            _waveOut.Play();
            return;
        }

        if (soundsGrid.SelectedItem is SoundItem item && DataContext is VoiceToolsViewModel vm)
            PlaySound(item, vm);
    }

    private void BtnStop_Click(object sender, RoutedEventArgs e) => StopAndCleanup();

    private void PlaySound(SoundItem item, VoiceToolsViewModel vm)
    {
        StopAndCleanup();

        try
        {
            // Get the raw sound data from the archive via reflection-free approach:
            // The archive stores sounds by name, we can access it through the ViewModel's bound data.
            // We need to extract the sound data. The simplest way: extract to temp file.
            var archiveField = typeof(VoiceToolsViewModel).GetField("_archive",
                System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            var archive = archiveField?.GetValue(vm) as DokaponSoFTools.Core.Formats.PckArchive;

            if (archive is null) return;

            var sound = archive.Sounds.FirstOrDefault(s => s.Name == item.Name);
            if (sound is null) return;

            _tempFile = Path.Combine(Path.GetTempPath(), $"dokapon_preview_{Guid.NewGuid():N}.ogg");
            File.WriteAllBytes(_tempFile, sound.Data);

            _vorbisReader = new VorbisWaveReader(_tempFile);
            _waveOut = new WaveOutEvent();
            _waveOut.Init(_vorbisReader);
            _waveOut.PlaybackStopped += (_, _) =>
            {
                Dispatcher.Invoke(() => nowPlayingText.Text = "");
            };
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
        _vorbisReader?.Dispose();
        _vorbisReader = null;

        if (_tempFile is not null && File.Exists(_tempFile))
        {
            try { File.Delete(_tempFile); } catch { }
            _tempFile = null;
        }

        nowPlayingText.Text = "";
    }
}
