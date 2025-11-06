from flask import Flask, request, jsonify
from ultralytics import YOLO
import cv2
import requests
from datetime import datetime

# proverimo da li imamo GPU
try:
    import torch
    HAS_CUDA = torch.cuda.is_available()
except Exception:
    HAS_CUDA = False

app = Flask(__name__)

# ucitavanje modela
model = YOLO("yolov8n.pt")
if HAS_CUDA:
    model.to("cuda")
    print("YOLO radi na CUDA")
else:
    print("YOLO radi na CPU")

# mapa kamera -> rtsp
CAMERA_RTSP_MAP = {
    "CAM_WH_01": "rtsp://user:pass@192.168.1.51/stream1",
    "CAM_GATE_01": "rtsp://user:pass@192.168.1.52/stream1",
}

# C# middleware
MIDDLEWARE_URL = "http://192.168.1.100:5000/ai-event"

# podrazumevano vreme gledanja
DEFAULT_DURATION = 10  # sekundi

# preskakanje frejmova radi brzine
FRAME_SKIP = 3

# tvoji sabloni
TPL_PERSON = 17   # "Nepoznato lice se zadrzava..."
TPL_ANIMAL = 1    # "Zivotinje"
TPL_BIRD = 2      # "Ptice"
TPL_GREEN = 5     # "Zelenilo"

# klase
GREEN_CLASSES = {"potted plant", "plant", "tree", "bush"}
DOG_CAT_CLASSES = {"dog", "cat"}

# prag za "ovo je dovoljno ozbiljno da prekidamo odmah"
EARLY_PERSON_CONF = 0.7


def send_to_middleware(template_id, cam_name, confidence):
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
        print("greska slanja u middleware:", e)


def analyze_camera(rtsp_url, cam_name, duration_sec=10):
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print("ne mogu da otvorim rtsp za", cam_name)
        return

    start_time = datetime.utcnow()

    people_conf = []
    animal_conf = []
    bird_conf = []
    green_conf = []

    frame_id = 0

    while (datetime.utcnow() - start_time).total_seconds() < duration_sec:
        ret, frame = cap.read()
        if not ret:
            break

        frame_id += 1
        if frame_id % FRAME_SKIP != 0:
            continue

        frame = cv2.resize(frame, (640, 360))

        results = model(frame, verbose=False)

        for r in results:
            for b in r.boxes:
                cls_id = int(b.cls[0])
                cls_name = model.names[cls_id]
                conf = float(b.conf[0])

                if conf < 0.5:
                    continue

                # 1) covek -> cuvamo, ali i proveravamo EARLY EXIT
                if cls_name == "person":
                    people_conf.append(conf)

                    # EARLY EXIT: ako je ozbiljan covek, odmah saljemo i prekidamo sve
                    if conf >= EARLY_PERSON_CONF:
                        cap.release()
                        send_to_middleware(TPL_PERSON, cam_name, conf)
                        return
                    continue

                # 2) pas / macka
                if cls_name in DOG_CAT_CLASSES:
                    animal_conf.append(conf)
                    continue

                # 3) ptica
                if cls_name == "bird":
                    bird_conf.append(conf)
                    continue

                # 4) zelenilo
                if cls_name in GREEN_CLASSES:
                    green_conf.append(conf)
                    continue

    cap.release()

    # ako nista nismo nasli
    if not (people_conf or animal_conf or bird_conf or green_conf):
        print("AI nije nasao nista korisno na", cam_name)
        return

    # PRIORITET posle gledanja celog klipa:
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

    send_to_middleware(template_id, cam_name, confidence)


@app.route("/bvms-event", methods=["POST"])
def bvms_event():
    data = request.get_json(force=True)
    cam_name = data.get("camera")
    if not cam_name:
        return jsonify({"error": "camera missing"}), 400

    rtsp = CAMERA_RTSP_MAP.get(cam_name)
    if not rtsp:
        return jsonify({"error": "unknown camera"}), 400

    duration = data.get("duration", DEFAULT_DURATION)
    analyze_camera(rtsp, cam_name, duration_sec=duration)
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
