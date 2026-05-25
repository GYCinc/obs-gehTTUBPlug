#!/home/hayron/MyProjects/obsmeets/.venv/bin/python3
"""OBS Controller — starts virtual cam + recording, then waits."""

import obsws_python as obs
import signal
import sys
import time

OBS_HOST = "localhost"
OBS_PORT = 4455
OBS_PASSWORD = "Ff9HX6pAjUvL8oyx"


def main():
    cl = None
    try:
        cl = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD)
        print("Connected to OBS")
        try:
            cl.start_virtual_cam()
            print("Virtual camera started")
        except Exception:
            print("Virtual camera already running")
        try:
            cl.start_record()
            print("Recording started")
        except Exception:
            print("Recording already in progress")
    except Exception as e:
        print(f"OBS connection failed: {e}")
        sys.exit(1)

    def cleanup(*_):
        print("\nStopping...")
        if cl:
            try: cl.stop_record()
            except: pass
            try: cl.stop_virtual_cam()
            except: pass
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print("\nSession live. Use OBS Tools → Captions for live subtitles.")
    print("Ctrl+C to stop.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
