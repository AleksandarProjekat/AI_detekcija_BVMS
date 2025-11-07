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

# 1) MODEL
model = YOLO("yolov8n.pt")  # promeni ako imas drugi

# 2) CUDA
try:
    import torch
    if torch.cuda.is_available():
        model.to("cuda")
        print("YOLO na CUDA")
    else:
        print("YOLO na CPU")
except Exception:
    print("YOLO na CPU (nema torch)")

# 3) KONFIG
with open('config.json', 'r') as file:
    data = json.load(file)

CAP_REGION = {
    "top": data["CAP_REGION"]["top"],
    "left": data["CAP_REGION"]["left"],
    "width": data["CAP_REGION"]["width"],
    "height": data["CAP_REGION"]["height"]
}

BUFFER_SECONDS = data["SCREEN_OPTIONS"]["BUFFER_SECONDS"]
CAP_FPS = data["SCREEN_OPTIONS"]["CAP_FPS"]

MAX_FRAMES = BUFFER_SECONDS * CAP_FPS

frame_buffer = deque(maxlen=MAX_FRAMES)
buffer_lock = threading.Lock()

# MIDDLEWARE_URL = data["MIDDLEWARE_URL"]

TPL_PERSON = 17
TPL_ANIMAL = 1
TPL_BIRD = 2
TPL_GREEN = 5
TPL_CAR = 15

DOG_CAT_CLASSES = {"dog", "cat"}
GREEN_CLASSES = {"potted plant", "plant", "tree", "bush"}


def screen_capture_worker():
    with mss.mss() as sct:
        while True:
            img = sct.grab(CAP_REGION)
            frame = np.array(img)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            frame = cv2.resize(frame, (640, 360))
            with buffer_lock:
                frame_buffer.append(frame)
            time.sleep(1 / CAP_FPS)


def analyze_frames(frames, cam_name="BVMS_SCREEN"):
    if not frames:
        print("nema frejmova za analizu")
        return

    people_conf = []
    animal_conf = []
    bird_conf = []
    green_conf = []
    car_conf = []

    for frame in frames:
        results = model(frame, verbose=False)
        for r in results:
            for b in r.boxes:
                cls_id = int(b.cls[0])
                cls_name = model.names[cls_id]
                conf = float(b.conf[0])

                if conf < 0.4:
                    continue

                if cls_name == "person":
                    people_conf.append(conf)
                elif cls_name == "car":
                    car_conf.append(conf)
                elif cls_name in DOG_CAT_CLASSES:
                    animal_conf.append(conf)
                elif cls_name == "bird":
                    bird_conf.append(conf)
                elif cls_name in GREEN_CLASSES:
                    green_conf.append(conf)

    if not (people_conf or animal_conf or bird_conf or green_conf or car_conf):
        print("nista nije nadjeno u BVMS prozoru")
        return

    if people_conf:
        template_id = TPL_PERSON
        confidence = max(people_conf)
    elif car_conf:
        template_id = TPL_CAR
        confidence = max(car_conf)
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
        # requests.post(MIDDLEWARE_URL, json=payload, timeout=2)
        print("poslato u middleware:", payload)
    except Exception as e:
        print("greska slanja:", e)


def handle_bvms_event(cam_name):
    # ocisti
    with buffer_lock:
        frame_buffer.clear()

    # cekaj da se napuni
    time.sleep(BUFFER_SECONDS)

    # uzmi frejmove
    with buffer_lock:
        frames_to_process = list(frame_buffer)
        frame_buffer.clear()

    analyze_frames(frames_to_process, cam_name)


@app.route("/bvms-event", methods=["POST"])
def bvms_event():
    data_req = request.get_json(force=True)
    cam_name = data_req.get("camera", "BVMS_SCREEN")

    th = threading.Thread(target=handle_bvms_event, args=(cam_name,))
    th.daemon = True
    th.start()

    return jsonify({"status": "accepted"})


if __name__ == "__main__":
    t = threading.Thread(target=screen_capture_worker, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=8000)
