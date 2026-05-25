#!/home/hayron/MyProjects/obsmeets/.venv/bin/python3
import obsws_python as obs, signal, sys, time, json, threading
import pyaudio, websocket

KEY = "b35aa6a95eed4a40aae9550e01360dac"
cl = obs.ReqClient(host="localhost", port=4455, password="Ff9HX6pAjUvL8oyx")

s = cl.get_virtual_cam_status()
if not getattr(s, 'output_active', False):
    cl.start_virtual_cam()

scenes = cl.get_scene_list()
try:
    cl.create_input(scenes.scenes[0]['sceneName'], 'Subtitles', 'text_ft2_source_v2',
        inputSettings={'text': '', 'font': {'size': 56, 'face': 'Sans'}, 'color': 4294967295},
        sceneItemEnabled=True)
except: pass

cl.start_record()

stop = threading.Event()
audio = pyaudio.PyAudio()
stream = audio.open(input=True, frames_per_buffer=800, channels=1,
                    format=pyaudio.paInt16, rate=16000)

def on_open(ws):
    def feed():
        while not stop.is_set():
            ws.send(stream.read(800, exception_on_overflow=False),
                    websocket.ABNF.OPCODE_BINARY)
    threading.Thread(target=feed, daemon=True).start()

def on_message(ws, msg):
    data = json.loads(msg)
    if data.get("type") == "Turn":
        text = data.get("transcript", "")
        if text.strip():
            cl.set_input_settings("Subtitles", {"text": text.strip()}, overlay=True)

def on_error(ws, e): stop.set()
def on_close(ws, c, m): stop.set()

ws = websocket.WebSocketApp(
    "wss://streaming.assemblyai.com/v3/ws?sample_rate=16000&speech_model=u3-rt-pro",
    header={"Authorization": KEY},
    on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close)

threading.Thread(target=ws.run_forever, daemon=True).start()

def cleanup(*_):
    stop.set()
    cl.stop_record()
    stream.stop_stream(); stream.close(); audio.terminate()
    ws.close()
    print("Saved."); sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)
print("Live. Virtual cam + recording + subtitles. Ctrl+C to stop.")
while True: time.sleep(1)
