"""
Video Converter for DOKAPON! Sword of Fury
Converts video files to game-compatible OGV format (Theora/Vorbis).

Conversion pipeline:
1. Input (any format) -> Standardized MP4 (720p, 29.97fps)
2. MP4 -> OGV (Theora video + Vorbis audio)

Author: DiNaSoR
License: Free to use and modify
"""

import os
import subprocess
import shutil
import tempfile
from dataclasses import dataclass
from typing import Optional, Callable, List, Tuple
from pathlib import Path


@dataclass
class VideoInfo:
    """Information about a video file."""
    path: str
    width: int = 0
    height: int = 0
    duration: float = 0.0
    fps: float = 0.0
    codec: str = ""
    audio_codec: str = ""
    file_size: int = 0
    
    @classmethod
    def from_file(cls, path: str, ffprobe_path: str = "ffprobe") -> 'VideoInfo':
        """
        Get video information using ffprobe.
        
        Args:
            path: Path to video file
            ffprobe_path: Path to ffprobe executable
            
        Returns:
            VideoInfo object with file metadata
        """
        info = cls(path=path)
        
        if not os.path.exists(path):
            return info
        
        info.file_size = os.path.getsize(path)
        
        try:
            # Get video stream info
            cmd = [
                ffprobe_path,
                "-v", "quiet",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,r_frame_rate,codec_name,duration",
                "-of", "csv=p=0",
                path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(',')
                if len(parts) >= 4:
                    info.width = int(parts[0]) if parts[0] else 0
                    info.height = int(parts[1]) if parts[1] else 0
                    
                    # Parse frame rate (may be fraction like "30000/1001")
                    if parts[2] and '/' in parts[2]:
                        num, den = parts[2].split('/')
                        info.fps = float(num) / float(den) if float(den) > 0 else 0
                    elif parts[2]:
                        info.fps = float(parts[2])
                    
                    info.codec = parts[3] if len(parts) > 3 else ""
                    
                    if len(parts) > 4 and parts[4]:
                        info.duration = float(parts[4])
            
            # Get audio codec
            cmd_audio = [
                ffprobe_path,
                "-v", "quiet",
                "-select_streams", "a:0",
                "-show_entries", "stream=codec_name",
                "-of", "csv=p=0",
                path
            ]
            result_audio = subprocess.run(cmd_audio, capture_output=True, text=True, timeout=30)
            if result_audio.returncode == 0:
                info.audio_codec = result_audio.stdout.strip()
                
        except Exception as e:
            print(f"Error getting video info: {e}")
        
        return info
    
    @property
    def resolution(self) -> str:
        """Get resolution as string (e.g., '1280x720')."""
        return f"{self.width}x{self.height}"
    
    @property
    def duration_str(self) -> str:
        """Get duration as formatted string (MM:SS)."""
        minutes = int(self.duration // 60)
        seconds = int(self.duration % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    @property
    def file_size_str(self) -> str:
        """Get file size as formatted string."""
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"


@dataclass
class ConversionSettings:
    """Settings for video conversion."""
    width: int = 1280
    height: int = 720
    fps: float = 29.97
    video_quality: int = 8       # Theora quality (0-10, higher = better)
    audio_quality: int = 4       # Vorbis quality (0-10, higher = better)
    audio_sample_rate: int = 48000
    maintain_aspect: bool = True
    
    @classmethod
    def default(cls) -> 'ConversionSettings':
        """Get default settings matching game requirements."""
        return cls()
    
    @classmethod
    def high_quality(cls) -> 'ConversionSettings':
        """Get high quality settings."""
        return cls(video_quality=9, audio_quality=6)
    
    @classmethod
    def fast(cls) -> 'ConversionSettings':
        """Get fast conversion settings (lower quality)."""
        return cls(video_quality=5, audio_quality=3)


class VideoConverter:
    """
    Handles video conversion to game-compatible OGV format.
    
    Uses FFmpeg for all conversions.
    """
    
    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        """
        Initialize the video converter.
        
        Args:
            ffmpeg_path: Path to ffmpeg executable
            ffprobe_path: Path to ffprobe executable
        """
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
    
    def verify_tools(self) -> Tuple[bool, str]:
        """
        Verify that FFmpeg tools are available.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Check ffmpeg
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                return False, "FFmpeg not working properly"
            
            # Check ffprobe
            result = subprocess.run(
                [self.ffprobe_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                return False, "FFprobe not working properly"
            
            return True, "FFmpeg tools verified"
            
        except FileNotFoundError:
            return False, "FFmpeg not found. Please ensure FFmpeg is installed."
        except subprocess.TimeoutExpired:
            return False, "FFmpeg timed out"
        except Exception as e:
            return False, f"Error verifying FFmpeg: {e}"
    
    def get_video_info(self, path: str) -> VideoInfo:
        """Get information about a video file."""
        return VideoInfo.from_file(path, self.ffprobe_path)
    
    def convert_to_mp4(self, input_path: str, output_path: str,
                       settings: ConversionSettings = None,
                       progress_callback: Callable[[float], None] = None) -> bool:
        """
        Convert video to standardized MP4 format.
        
        Args:
            input_path: Path to input video
            output_path: Path for output MP4
            settings: Conversion settings
            progress_callback: Optional callback for progress updates (0.0-1.0)
            
        Returns:
            True if successful, False otherwise
        """
        if settings is None:
            settings = ConversionSettings.default()
        
        # Build video filter for scaling
        if settings.maintain_aspect:
            vf = (f"scale={settings.width}:{settings.height}:"
                  f"force_original_aspect_ratio=decrease,"
                  f"pad={settings.width}:{settings.height}:(ow-iw)/2:(oh-ih)/2,"
                  f"setsar=1")
        else:
            vf = f"scale={settings.width}:{settings.height},setsar=1"
        
        cmd = [
            self.ffmpeg_path,
            "-y",  # Overwrite output
            "-i", input_path,
            "-vf", vf,
            "-r", str(settings.fps),
            "-ar", str(settings.audio_sample_rate),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output_path
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        except Exception as e:
            print(f"MP4 conversion error: {e}")
            return False
    
    def convert_mp4_to_ogv(self, input_path: str, output_path: str,
                          settings: ConversionSettings = None,
                          progress_callback: Callable[[float], None] = None) -> bool:
        """
        Convert MP4 to OGV (Theora/Vorbis) format.
        
        Args:
            input_path: Path to input MP4
            output_path: Path for output OGV
            settings: Conversion settings
            progress_callback: Optional callback for progress updates
            
        Returns:
            True if successful, False otherwise
        """
        if settings is None:
            settings = ConversionSettings.default()
        
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", input_path,
            "-c:v", "libtheora",
            "-q:v", str(settings.video_quality),
            "-c:a", "libvorbis",
            "-q:a", str(settings.audio_quality),
            "-ac", "2",  # Stereo audio
            output_path
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        except Exception as e:
            print(f"OGV conversion error: {e}")
            return False
    
    def convert_to_game_format(self, input_path: str, output_path: str,
                               settings: ConversionSettings = None,
                               progress_callback: Callable[[float], None] = None,
                               keep_temp: bool = False) -> Tuple[bool, str]:
        """
        Full conversion pipeline: Input -> MP4 -> OGV
        
        Args:
            input_path: Path to input video (any format)
            output_path: Path for output OGV file
            settings: Conversion settings
            progress_callback: Optional callback for progress updates
            keep_temp: Whether to keep intermediate MP4 file
            
        Returns:
            Tuple of (success, message)
        """
        if settings is None:
            settings = ConversionSettings.default()
        
        if not os.path.exists(input_path):
            return False, f"Input file not found: {input_path}"
        
        # Create temp directory for intermediate file
        temp_dir = tempfile.mkdtemp(prefix="dokapon_video_")
        temp_mp4 = os.path.join(temp_dir, "temp_video.mp4")
        
        try:
            # Step 1: Convert to standardized MP4
            if progress_callback:
                progress_callback(0.1)
            
            if not self.convert_to_mp4(input_path, temp_mp4, settings):
                return False, "Failed to convert to MP4"
            
            if progress_callback:
                progress_callback(0.5)
            
            # Step 2: Convert MP4 to OGV
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            
            if not self.convert_mp4_to_ogv(temp_mp4, output_path, settings):
                return False, "Failed to convert to OGV"
            
            if progress_callback:
                progress_callback(1.0)
            
            # Verify output
            if not os.path.exists(output_path):
                return False, "Output file was not created"
            
            output_size = os.path.getsize(output_path)
            if output_size == 0:
                return False, "Output file is empty"
            
            return True, f"Successfully converted to {output_path}"
            
        except Exception as e:
            return False, f"Conversion error: {e}"
        
        finally:
            # Cleanup temp files
            if not keep_temp:
                try:
                    if os.path.exists(temp_mp4):
                        os.remove(temp_mp4)
                    os.rmdir(temp_dir)
                except:
                    pass


def find_game_videos(game_dir: str) -> List[str]:
    """
    Find all OGV video files in a game directory.
    
    Args:
        game_dir: Path to game installation directory
        
    Returns:
        List of paths to OGV files
    """
    ogv_files = []
    
    # Common locations for game videos
    search_paths = [
        game_dir,
        os.path.join(game_dir, "GameData", "app"),
        os.path.join(game_dir, "data"),
        os.path.join(game_dir, "movies"),
    ]
    
    for search_path in search_paths:
        if os.path.exists(search_path):
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    if file.lower().endswith('.ogv'):
                        ogv_files.append(os.path.join(root, file))
    
    return sorted(set(ogv_files))


def backup_video(video_path: str, backup_dir: str = None) -> Optional[str]:
    """
    Create a backup of a video file.
    
    Args:
        video_path: Path to video to backup
        backup_dir: Backup directory (defaults to same directory with .backup extension)
        
    Returns:
        Path to backup file, or None if backup failed
    """
    if not os.path.exists(video_path):
        return None
    
    if backup_dir:
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, os.path.basename(video_path))
    else:
        backup_path = video_path + ".backup"
    
    # Don't overwrite existing backup
    if os.path.exists(backup_path):
        return backup_path
    
    try:
        shutil.copy2(video_path, backup_path)
        return backup_path
    except Exception as e:
        print(f"Backup error: {e}")
        return None


def get_supported_input_formats() -> List[str]:
    """Get list of supported input video formats."""
    return [
        ".mp4", ".avi", ".mkv", ".mov", ".wmv", 
        ".flv", ".webm", ".m4v", ".mpeg", ".mpg"
    ]

