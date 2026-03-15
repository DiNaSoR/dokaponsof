from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from ..widgets.scrolling_text import ScrollingTextWidget
import os
import sys


class AboutTab(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()
        self._setup_music()

    def _setup_music(self):
        """Setup background music"""
        try:
            # Get the application base path (works in both script and frozen exe)
            if getattr(sys, 'frozen', False):
                # Running as compiled exe
                base_path = sys._MEIPASS
            else:
                # Running as script - go up to app/ directory then into resources/
                base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            
            # Update music path - resources is inside the app folder
            music_path = os.path.join(base_path, "app", "resources", "bgm.mp3")
            
            # Fallback: try the frozen exe path structure
            if not os.path.exists(music_path):
                music_path = os.path.join(base_path, "resources", "bgm.mp3")
            
            if os.path.exists(music_path):
                self.media_player = QMediaPlayer()
                self.audio_output = QAudioOutput()
                self.media_player.setAudioOutput(self.audio_output)
                self.media_player.setSource(QUrl.fromLocalFile(str(music_path)))
                
                # Set audio output properties
                self.audio_output.setVolume(0.5)  # 50% volume
                
                # Connect signals after source is set
                self.media_player.errorOccurred.connect(self._handle_media_error)
                self.media_player.mediaStatusChanged.connect(self._on_media_status_changed)
                
                # Initial play and pause to setup format
                self.media_player.play()
                self.media_player.pause()
                    
        except Exception as e:
            print(f"Music setup error: {str(e)}")

    def _handle_media_error(self, error, error_string):
        """Handle media player errors quietly"""
        if error != QMediaPlayer.Error.NoError:
            print(f"Media error: {error_string}")

    def _on_media_status_changed(self, status):
        """Handle music looping"""
        try:
            if status == QMediaPlayer.MediaStatus.EndOfMedia:
                self.media_player.setPosition(0)
                self.media_player.play()
        except Exception as e:
            print(f"Media status error: {str(e)}")

    def showEvent(self, event):
        """Start playing when tab is shown"""
        super().showEvent(event)
        if hasattr(self, 'media_player'):
            self.media_player.play()

    def toggle_music(self):
        """Toggle music mute state"""
        if hasattr(self, 'audio_output'):
            self.audio_output.setMuted(not self.audio_output.isMuted())

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        about_text = """


        ██████╗  ██████╗ ██╗  ██╗ █████╗ ██████╗  ██████╗ ███╗   ██╗
        ██╔══██╗██╔═══██╗██║ ██╔╝██╔══██╗██╔══██╗██╔═══██╗████╗  ██║
        ██║  ██║██║   ██║█████╔╝ ███████║██████╔╝██║   ██║██╔██╗ ██║
        ██║  ██║██║   ██║██╔═██╗ ██╔══██║██╔═══╝ ██║   ██║██║╚██╗██║
        ██████╔╝╚██████╔╝██║  ██╗██║  ██║██║     ╚██████╔╝██║ ╚████║
        ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝      ╚═════╝ ╚═╝  ╚═══╝

              ███████╗ ██████╗ ███████╗
              ██╔════╝██╔═══██╗██╔════╝
              ███████╗██║   ██║█████╗
              ╚════██║██║   ██║██╔══╝
              ███████║╚██████╔╝██║
              ╚══════╝ ╚═════╝ ╚═╝

      ╔══════════════════════════════════════════╗
      ║     S W O R D   O F   F U R Y           ║
      ║            M O D   T O O L S            ║
      ║                                          ║
      ║            v 0 . 4 . 0                   ║
      ╚══════════════════════════════════════════╝


                  ░░░▒▒▒▓▓███▓▓▒▒▒░░░
               ░▒▓█                   █▓▒░
              ▒█     ╔═══╗            █▒
             ▓█      ║ D ║ i N a S o R █▓
              ▒█     ╚═══╝            █▒
               ░▒▓█                   █▓▒░
                  ░░░▒▒▒▓▓███▓▓▒▒▒░░░


 ┌──────────────────────────────────────────────┐
 │          A B O U T   T H E   D E V           │
 └──────────────────────────────────────────────┘

        Hey there! I'm DiNaSoR, a passionate
        developer who loves working on game
        modding tools.

        This tool was created to help the
        Dokapon community with file extraction,
        asset exploration, and modding.


          ██▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀██
          ██   F E A T U R E S      ██
          ██▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄██

           Asset Extractor
             .tex  .spranm  .mpd  .fnt

           Text Editor
             Extract, edit, reimport

           Voice Tools
             PCK extraction & replacement

           3D Model Viewer
             MDL geometry preview

           Video Converter
             Cutscene replacement

           Map Explorer        [NEW]
             Cell atlas & map rendering

           Hex Editor
             Binary patch management


 ┌──────────────────────────────────────────────┐
 │       F I N D   M E   O N L I N E            │
 └──────────────────────────────────────────────┘

            ┌───────────────────┐
            │    G i t H u b    │
            └───────────────────┘
       github.com/DiNaSoR/dokaponsof

            ┌───────────────────┐
            │   D i s c o r d   │
            └───────────────────┘
         discord.gg/wXhAEvhTuR

            ┌───────────────────┐
            │   R e d d i t     │
            └───────────────────┘
         r/dokaponofficial


 ┌──────────────────────────────────────────────┐
 │    S U P P O R T   D E V E L O P M E N T    │
 └──────────────────────────────────────────────┘

        If you find this tool helpful,
        consider supporting its development:

            PayPal: dragonarab@gmail.com

            Every bit helps keep the
            project alive and growing!


 ┌──────────────────────────────────────────────┐
 │        S P E C I A L   T H A N K S           │
 └──────────────────────────────────────────────┘

        To the Dokapon community for their
        support, feedback, and passion!

        To q8fft2 for the original text
        extraction research.

        To everyone who reported bugs and
        suggested features.


           ░▒▓█ Thank you all! █▓▒░


         ╔═╗╔═╗╔═╗╔═╗  ╔╦╗╔═╗╔╦╗╔╦╗╦╔╗╔╔═╗
         ╠═╝╠═╝╠═╝╠═╝  ║║║║ ║ ║║ ║║║║║║║ ╦
         ╩  ╩  ╩  ╩     ╩ ╩╚═╝═╩╝═╩╝╩╝╚╝╚═╝

                   ♫ ♫ ♫ ♫ ♫


      ╔══════════════════════════════════════════╗
      ║                                          ║
      ║        Press  F  to pay respects         ║
      ║                                          ║
      ╚══════════════════════════════════════════╝


"""
        
        # Remove any leading spaces from each line
        about_text = '\n'.join(line.lstrip() for line in about_text.split('\n'))
        
        self.scroller = ScrollingTextWidget(about_text)
        
        layout.addWidget(self.scroller) 