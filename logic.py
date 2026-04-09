import json
import os
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl, QTimer
from PyQt6.QtWidgets import QFileDialog

class LogicHandler:
    def __init__(self, window):
        self.window = window
        self.is_playing = False
        
        self.audio_output = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)
        
        self.playlist = []
        self.current_index = -1
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_position)
        self.timer.start(500)

        self.player.mediaStatusChanged.connect(self._status_changed)

    def handle_click(self, data_str):
        try:
            d = json.loads(data_str)
            idx = d.get("idx")
            func = d.get("function")
            if func == "button" and hasattr(self, idx):
                getattr(self, idx)()
        except Exception as e:
            print(f"Ошибка логики: {e}")

    def dir(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("Audio (*.mp3 *.wav *.ogg *.m4a *.flac)")
        
        if file_dialog.exec():
            files = file_dialog.selectedFiles()
            if files:
                self.playlist = files
                self.current_index = 0
                self.load_track()

    def load_track(self):
        if 0 <= self.current_index < len(self.playlist):
            path = self.playlist[self.current_index]
            self.player.setSource(QUrl.fromLocalFile(path))
            self.play_pause(force_play=True)
            
            name = os.path.basename(path)
            self.run_js(f"document.querySelector('[idx=\"currently_playing\"]').textContent='Playing: {name}'")

    def play_pause(self, force_play=False):
        if force_play: self.is_playing = False
        
        if self.is_playing:
            self.player.pause()
            self.is_playing = False
            self.window.update_ui_state("event_pause")
        else:
            self.player.play()
            self.is_playing = True
            self.window.update_ui_state("event_play")

    def stop(self):
        self.player.stop()
        self.is_playing = False
        self.window.update_ui_state("event_stop")

    def back(self): self.player.setPosition(max(0, self.player.position() - 5000))
    def forward(self): self.player.setPosition(min(self.player.duration(), self.player.position() + 5000))

    def begin(self):
        self.player.setPosition(0)
        
    def end(self):
        if self.current_index < len(self.playlist) - 1:
            self.current_index += 1
            self.load_track()

    def minus(self): self.window.change_scale(-0.5)
    def plus(self): self.window.change_scale(0.5)
    def close(self): self.window.close()

    def _status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.end()

    def update_position(self):
        if self.player.duration() > 0:
            pos = self.format_time(self.player.position())
            dur = self.format_time(self.player.duration())
            self.run_js(f"document.querySelector('[idx=\"timer\"]').textContent='{pos} / {dur}'")

    def format_time(self, ms):
        s = ms // 1000
        m, s = divmod(s, 60)
        return f"{m:02d}:{s:02d}"

    def run_js(self, code):
        self.window.browser.page().runJavaScript(code)