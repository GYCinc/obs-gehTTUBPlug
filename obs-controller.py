#!/home/hayron/MyProjects/obsmeets/.venv/bin/python3
"""OBS Controller — start recording, wait, stop on exit."""
import obsws_python as obs
import signal, sys, time

cl = obs.ReqClient(host="localhost", port=4455, password="Ff9HX6pAjUvL8oyx")
print(f"OBS {cl.get_version().obs_version} connected")
cl.start_record()
print("Recording started")

def cleanup(*_):
    cl.stop_record()
    print("Recording saved")
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)
while True:
    time.sleep(1)
