from flask import Flask, request, jsonify
from ultralytics import YOLO
from collections import deque
from datetime import datetime
import threading
import json
import requests
import time
import mss
import cv2
import numpy as np

app = Flask(__name__)

# 1) UCITAJ YOLO MODEL
# stavi model koji imas (ti si naveo "yolo11x.pt")
model = YOLO("yolo11x.pt")

# 2) PROVERA CUDA
try:
    import torch
    if torch.cuda.is_available():
        model.to("cuda")
        print("YOLO na CUDA")
    else:
        print("YOLO na CPU")
except Exception:
    print("YOLO na CPU (nema torch)")

# 3) UCITAJ KONFIG
with open('config.json', 'r') as file:
    data = json.load(file)

# region ekrana gde BVMS prikazuje video
CAP_REGION = {
    "top": data["CAP_REGION"]["top"],
    "left": data["CAP_REGION"]["left"],
    "width": data["CAP_REGION"]["width"],
    "height": data["CAP_REGION"]["height"]
}

# koliko sekundi hocemo da snimamo POSLE eventa
BUFFER_SECONDS = data["SCREEN_OPTIONS"]["BUFFER_SECONDS"]  # npr. 10
# koliko puta u sekundi da slikamo ekran
CAP_FPS = data["SCREEN_OPTIONS"]["CAP_FPS"]                # npr. 5

# maksimalan broj frejmova koje čuvamo
MAX_FRAMES = BUFFER_SECONDS * CAP_FPS

# zajednički bafer i lock
frame_buffer = deque(maxlen=MAX_FRAMES)
buffer_lock = threading.Lock()

# tvoj middleware (C#)
MIDDLEWARE_URL = data["MIDDLEWARE_URL"]

# template ID-jevi iz tvog sistema
TPL_PERSON = 17   # covek
TPL_ANIMAL = 1    # pas/macka -> "Zivotinje"
TPL_BIRD = 2      # ptice
TPL_GREEN = 5     # zelenilo (fallback)

DOG_CAT_CLASSES = {"dog", "cat"}
GREEN_CLASSES = {"potted plant", "plant", "tree", "bush"}


def screen_capture_worker():
    """
    Pozadinski thread koji stalno hvata BVMS prozor sa ekrana
    i puni frame_buffer. Mi posle samo uzmemo to iz bafera.
    """
    with mss.mss() as sct:
        while True:
            img = sct.grab(CAP_REGION)
            frame = np.array(img)
            # BVMS ide kao BGRA pa ga prebacimo u BGR
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            # smanji radi brzeg YOLO
            frame = cv2.resize(frame, (640, 360))

            with buffer_lock:
                frame_buffer.append(frame)

            time.sleep(1 / CAP_FPS)


def analyze_frames(frames, cam_name="BVMS_SCREEN"):
    """
    Analiziraj tacno ove frejmove (ne globalni bafer).
    """
    if not frames:
        print("nema frejmova za analizu")
        return

    people_conf = []
    animal_conf = []
    bird_conf = []
    green_conf = []

    for frame in frames:
        results = model(frame, verbose=False)
        for r in results:
            for b in r.boxes:
                cls_id = int(b.cls[0])
                cls_name = model.names[cls_id]
                conf = float(b.conf[0])

                # ako je slabo, preskoci
                if conf < 0.4:
                    continue

                if cls_name == "person":
                    people_conf.append(conf)
                elif cls_name in DOG_CAT_CLASSES:
                    animal_conf.append(conf)
                elif cls_name == "bird":
                    bird_conf.append(conf)
                elif cls_name in GREEN_CLASSES:
                    green_conf.append(conf)

    # ako bas nista
    if not (people_conf or animal_conf or bird_conf or green_conf):
        print("nista nije nadjeno u BVMS prozoru")
        return

    # PRIORITETI:
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
        # kad budes hteo da saljes u C#, samo skini komentar
        # requests.post(MIDDLEWARE_URL, json=payload, timeout=2)
        print("poslato u middleware:", payload)
    except Exception as e:
        print("greska slanja:", e)


@app.route("/bvms-event", methods=["POST"])
def bvms_event():
    """
    Kad BVMS kaze "ovaj alarm je dosao",
    mi od tog trenutka snimamo narednih BUFFER_SECONDS sekundi,
    pa tek onda analiziramo.
    """
    data_req = request.get_json(force=True)
    cam_name = data_req.get("camera", "BVMS_SCREEN")

    # 1) ocisti sta god da je bilo pre
    with buffer_lock:
        frame_buffer.clear()

    # 2) cekaj da se napuni narednih X sekundi
    time.sleep(BUFFER_SECONDS)

    # 3) uzmi to sto se skupilo
    with buffer_lock:
        frames_to_process = list(frame_buffer)
        frame_buffer.clear()

    # 4) analiziraj
    analyze_frames(frames_to_process, cam_name)

    return jsonify({"status": "ok"})


if __name__ == "__main__":
    # pokreni snimanje ekrana u pozadini
    t = threading.Thread(target=screen_capture_worker, daemon=True)
    t.start()

    # pokreni API
    app.run(host="0.0.0.0", port=8000)
