#!/home/hayron/MyProjects/obsmeets/.venv/bin/python3
"""OBS Controller — Preply session: virtual camera + live captions + dual audio."""

import json
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime

import obsws_python as obs
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions

# ── Config ──────────────────────────────────────────────────────────
OBS_HOST = "localhost"
OBS_PORT = 4455
OBS_PASSWORD = "Ff9HX6pAjUvL8oyx"
DEEPGRAM_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
VIRTUAL_CAM_DEVICE = "/dev/video10"

# Audio source names in OBS
MIC_SOURCE = "EMEET PIXY"
SYS_AUDIO_SOURCE = "System Audio"
SUBTITLE_SOURCE = "Subtitles"
CAM_SOURCE = "PIXY Camera"
SCENE_NAME = "Preply Session"


class OBSController:
    def __init__(self):
        self.cl = None
        self.recording = False
        self.subtitle_text = ""
        self.subtitle_timeout = None

    def connect(self):
        self.cl = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD)
        version = self.cl.get_version()
        print(f"Connected to OBS {version.obs_version}")

    def setup_scene(self):
        """Switch to the Preply scene. Set up once in OBS UI manually."""
        try:
            self.cl.set_current_program_scene(SCENE_NAME)
            print(f"Switched to scene: {SCENE_NAME}")
        except Exception:
            print(f"Scene '{SCENE_NAME}' not found. Create it in OBS first:")
            print("  Sources → + → Video Capture Device → /dev/video0")
            print("  Sources → + → Text (FreeType 2) → name it 'Subtitles'")
            print("  Sources → + → Audio Input Capture → EMEET PIXY")
            print("  Sources → + → Audio Output Capture → Ryzen monitor")
            print("  Save as scene collection: 'Preply Session'")
            sys.exit(1)

    def update_subtitle(self, text: str):
        """Push new subtitle text to OBS overlay."""
        try:
            self.cl.set_input_settings(SUBTITLE_SOURCE, {"text": text}, overlay=True)
        except Exception as e:
            print(f"  Subtitle update error: {e}")

    def start_virtual_camera(self):
        try:
            self.cl.start_virtual_cam()
            print("Virtual camera started → /dev/video10")
        except Exception as e:
            print(f"Virtual camera error: {e}")

    def stop_virtual_camera(self):
        try:
            self.cl.stop_virtual_cam()
            print("Virtual camera stopped")
        except Exception:
            pass

    def start_recording(self):
        filename = f"$HOME/Videos/preply-{datetime.now().strftime('%Y%m%d-%H%M%S')}.mkv"
        try:
            self.cl.start_record()
            self.recording = True
            print(f"Recording started")
        except Exception as e:
            print(f"Record error: {e}")

    def stop_recording(self):
        if self.recording:
            try:
                self.cl.stop_record()
                self.recording = False
                print("Recording stopped")
            except Exception as e:
                print(f"Stop record error: {e}")

    def disconnect(self):
        self.stop_virtual_camera()
        self.stop_recording()
        if self.cl:
            try:
                self.cl.disconnect()
            except Exception:
                pass


class DeepgramTranscriber:
    def __init__(self, api_key: str, on_transcript):
        self.api_key = api_key
        self.on_transcript = on_transcript
        self.dg = DeepgramClient(api_key)
        self.connection = None
        self._running = False

    def start(self):
        self._running = True
        self.connection = self.dg.listen.live.v("1")
        self.connection.on(LiveTranscriptionEvents.Transcript, self._on_message)
        self.connection.on(LiveTranscriptionEvents.Error, self._on_error)

        options = LiveOptions(
            model="nova-2",
            language="en",
            smart_format=True,
            interim_results=True,
            punctuate=True,
        )
        self.connection.start(options)
        self._thread = threading.Thread(target=self._feed_audio, daemon=True)
        self._thread.start()
        print("Deepgram STT started")

    def _feed_audio(self):
        """Pipe mic audio to Deepgram in a subprocess."""
        import subprocess as sp
        cmd = [
            "parec", "--format=s16le", "--rate=16000", "--channels=1",
            "--device=alsa_input.usb-EMEET_EMEET_PIXY_A260324000300108-02.pro-input-0"
        ]
        proc = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.DEVNULL)
        while self._running:
            data = proc.stdout.read(3200)
            if not data:
                break
            self.connection.send(data)
        proc.terminate()

    def _on_message(self, _, result):
        transcript = result.channel.alternatives[0].transcript
        if transcript:
            self.on_transcript(transcript)

    def _on_error(self, _, error):
        print(f"Deepgram error: {error}")

    def stop(self):
        self._running = False
        if self.connection:
            self.connection.finish()


def main():
    obs = OBSController()

    def on_transcript(text):
        obs.update_subtitle(text)

    transcriber = DeepgramTranscriber(DEEPGRAM_KEY, on_transcript)

    def cleanup(*_):
        print("\nShutting down...")
        transcriber.stop()
        obs.stop_virtual_camera()
        obs.stop_recording()
        obs.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print("=== obsmeets controller ===")
    obs.connect()
    obs.setup_scene()
    obs.start_virtual_camera()
    obs.start_recording()
    transcriber.start()

    print("\nSession live. Ctrl+C to stop.\n")
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
