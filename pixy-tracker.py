#!/home/hayron/MyProjects/obsmeets/.venv/bin/python3
"""EMEET PIXY face-tracking auto-framer for Linux."""

import subprocess
import sys
import time
from pathlib import Path

import cv2

DEVICE = "/dev/video0"
WIDTH, HEIGHT = 2560, 1440

PAN_MIN, PAN_MAX, PAN_STEP = -540000, 540000, 3600
TILT_MIN, TILT_MAX, TILT_STEP = -324000, 324000, 3600

DEAD_ZONE = 0.08
MOVE_SPEED = 0.15
SMOOTHING = 0.4
MIN_FACE_SIZE = 80

pan = 0
tilt = 0


def find_cascade() -> str:
    search = [
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml",
        Path(cv2.__file__).parent / "data" / "haarcascade_frontalface_default.xml",
        "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml",
        "/usr/local/share/opencv4/haarcascades/haarcascade_frontalface_default.xml",
    ]
    for p in search:
        path = str(p)
        if Path(path).exists():
            return path
    sys.exit("No Haar cascade found. Install opencv-data.")


def set_ptz(target_pan: int, target_tilt: int):
    global pan, tilt
    pan = max(PAN_MIN, min(PAN_MAX, target_pan))
    tilt = max(TILT_MIN, min(TILT_MAX, target_tilt))
    subprocess.run(
        ["v4l2-ctl", "-d", DEVICE, "-c", f"pan_absolute={pan}", "-c", f"tilt_absolute={tilt}"],
        capture_output=True,
    )


def clamp_to_step(val: int, step: int) -> int:
    return round(val / step) * step


def main():
    global pan, tilt

    cascade = cv2.CascadeClassifier(find_cascade())
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        sys.exit("Cannot open camera")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, 30)

    half_x = WIDTH / 2
    half_y = HEIGHT / 2
    target_pan = pan
    target_tilt = tilt

    print("PIXY Tracker running — press Q to quit")

    while True:
        ok, frame = cap.read()
        if not ok:
            continue

        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, 1.1, 5, minSize=(MIN_FACE_SIZE, MIN_FACE_SIZE))

        if len(faces) > 0:
            fx, fy, fw, fh = max(faces, key=lambda r: r[2] * r[3])
            face_cx = fx + fw / 2
            face_cy = fy + fh / 2

            dx_norm = (face_cx - half_x) / half_x
            dy_norm = (face_cy - half_y) / half_y

            if abs(dx_norm) > DEAD_ZONE:
                target_pan += int(dx_norm * PAN_MAX * MOVE_SPEED)
            if abs(dy_norm) > DEAD_ZONE:
                target_tilt += int(dy_norm * TILT_MAX * MOVE_SPEED)

            target_pan = max(PAN_MIN, min(PAN_MAX, target_pan))
            target_tilt = max(TILT_MIN, min(TILT_MAX, target_tilt))

            cv2.rectangle(frame, (fx, fy), (fx + fw, fy + fh), (0, 255, 0), 2)

        new_pan = pan + int((target_pan - pan) * SMOOTHING)
        new_tilt = tilt + int((target_tilt - tilt) * SMOOTHING)
        new_pan = clamp_to_step(new_pan, PAN_STEP)
        new_tilt = clamp_to_step(new_tilt, TILT_STEP)

        if new_pan != pan or new_tilt != tilt:
            set_ptz(new_pan, new_tilt)

        cv2.line(frame, (int(half_x) - 20, int(half_y)), (int(half_x) + 20, int(half_y)), (0, 0, 255), 1)
        cv2.line(frame, (int(half_x), int(half_y) - 20), (int(half_x), int(half_y) + 20), (0, 0, 255), 1)

        cv2.imshow("PIXY Tracker", cv2.resize(frame, (960, 540)))

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("r"):
            target_pan = 0
            target_tilt = 0
            print("Resetting to center")

    cap.release()
    cv2.destroyAllWindows()
    set_ptz(0, 0)
    print("Camera centered. Done.")


if __name__ == "__main__":
    main()
