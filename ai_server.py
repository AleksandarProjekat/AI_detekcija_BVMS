from flask import Flask, request, jsonify
from ultralytics import YOLO
from collections import deque
from datetime import datetime
import threading
import requests
import time
import mss
import cv2
import numpy as np

app = Flask(__name__)

# YOLO model
model = YOLO("yolov8n.pt")

# probaj CUDA
try:
    import torch
    if torch.cuda.is_available():
        model.to("cuda")
        print("YOLO na CUDA")
    else:
        print("YOLO na CPU")
except Exception:
    print("YOLO na CPU (nema torch)")

# OVDE PODESIS GDE JE BVMS VIDEO NA EKRANU
CAP_REGION = {"top": 150, "left": 300, "width": 800, "height": 450}

# koliko sekundi da cuvamo
BUFFER_SECONDS = 10
# koliko fps hocemo iz ekrana
CAP_FPS = 5
# znaci ukupno frejmova:
MAX_FRAMES = BUFFER_SECONDS * CAP_FPS

# u ovaj buffer pisemo frejmove koje BVMS prikazuje
frame_buffer = deque(maxlen=MAX_FRAMES)

# tvoji template ID-jevi
TPL_PERSON = 17
TPL_ANIMAL = 1
TPL_BIRD = 2
TPL_GREEN = 5

DOG_CAT_CLASSES = {"dog", "cat"}
GREEN_CLASSES = {"potted plant", "plant", "tree", "bush"}

MIDDLEWARE_URL = "http://192.168.1.100:5000/ai-event"


def screen_capture_worker():
    """Pozadinski thread koji stalno hvata BVMS prozor."""
    with mss.mss() as sct:
        while True:
            img = sct.grab(CAP_REGION)
            frame = np.array(img)
            # BVMS daje BGRA, YOLO ocekuje BGR
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            # smanji da brze radi YOLO
            frame = cv2.resize(frame, (640, 360))
            frame_buffer.append(frame)
            time.sleep(1 / CAP_FPS)


# pokreni thread
t = threading.Thread(target=screen_capture_worker, daemon=True)
t.start()


def analyze_frames(cam_name="BVMS_SCREEN"):
    """Analiziraj ono sto je BVMS prikazao u poslednjih 10 s."""
    if not frame_buffer:
        print("nema frejmova u bufferu")
        return

    people_conf = []
    animal_conf = []
    bird_conf = []
    green_conf = []

    # prodjemo kroz SVE sacuvane frejmove
    for frame in list(frame_buffer):
        results = model(frame, verbose=False)
        for r in results:
            for b in r.boxes:
                cls_id = int(b.cls[0])
                cls_name = model.names[cls_id]
                conf = float(b.conf[0])

                if conf < 0.5:
                    continue

                if cls_name == "person":
                    people_conf.append(conf)
                elif cls_name in DOG_CAT_CLASSES:
                    animal_conf.append(conf)
                elif cls_name == "bird":
                    bird_conf.append(conf)
                elif cls_name in GREEN_CLASSES:
                    green_conf.append(conf)

    if not (people_conf or animal_conf or bird_conf or green_conf):
        print("nista nije nadjeno u BVMS prozoru")
        return

    # prioritet
    if people_conf:
        template_id = TPL_PERSON
        confidence = max(people_conf)
    elif animal_conf:
        template_id = TPL_ANIMAL
        confidence = max(animal_conf)
    elif bird_conf:
        template_id = TPL_BIRD
        confidence = max(bird_conf)
    else:
        template_id = TPL_GREEN
        confidence = max(green_conf)

    payload = {
        "template_id": template_id,
        "camera": cam_name,
        "confidence": confidence,
        "timestamp": datetime.utcnow().isoformat()
    }

    try:
        requests.post(MIDDLEWARE_URL, json=payload, timeout=2)
        print("poslato u middleware:", payload)
    except Exception as e:
        print("greska slanja:", e)


@app.route("/bvms-event", methods=["POST"])
def bvms_event():
    data = request.get_json(force=True)
    cam_name = data.get("camera", "BVMS_SCREEN")
    # umesto da otvaramo RTSP, mi analiziramo ono sto vec imamo u bufferu
    analyze_frames(cam_name)
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    # flask server
    app.run(host="0.0.0.0", port=8000)
