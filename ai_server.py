### Ovaj server primi od skripte clientscript “CAM_WH_01”, uzme RTSP, pusti YOLO, odluci: ptice → 2, covek → 17 i posalje C# middleware-u.
# ai_server.py
from flask import Flask, request, jsonify
from ultralytics import YOLO
import cv2
import requests
from datetime import datetime

# probamo da vidimo da li imamo cuda
try:
    import torch
    HAS_CUDA = torch.cuda.is_available()
except Exception:
    HAS_CUDA = False

app = Flask(__name__)

# ucitavanje modela
model = YOLO("yolov8n.pt")

# ako ima gpu, prebaci
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

# tvoj C# middleware
MIDDLEWARE_URL = "http://192.168.1.100:5000/ai-event"

# default duzina snimanja ako klijent ne posalje
DEFAULT_DURATION = 10  # sekundi

# koliko frejmova da preskacemo (1 = svaki, 3 = svaki treci)
FRAME_SKIP = 3

# sabloni iz tvog templates.json
TPL_PERSON = 17   # "Nepoznato lice se zadrzava..."
TPL_ANIMAL = 1    # "Zivotinje" – pas/macka
TPL_BIRD = 2      # "Ptice"
TPL_GREEN = 5     # "Zelenilo (zbun, trava, grana, lisce)"

# zbir klase
GREEN_CLASSES = {"potted plant", "plant", "tree", "bush"}
DOG_CAT_CLASSES = {"dog", "cat"}


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
        # preskoci neke frejmove da bude brze
        if frame_id % FRAME_SKIP != 0:
            continue

        # smanji rezoluciju
        frame = cv2.resize(frame, (640, 360))

        # YOLO infer
        # ako ima cuda, ovo ce biti bitno brze
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
                    continue

                if cls_name in DOG_CAT_CLASSES:
                    animal_conf.append(conf)
                    continue

                if cls_name == "bird":
                    bird_conf.append(conf)
                    continue

                if cls_name in GREEN_CLASSES:
                    green_conf.append(conf)
                    continue

    cap.release()

    # ako nista nema
    if not (people_conf or animal_conf or bird_conf or green_conf):
        print("AI nije nasao nista korisno na", cam_name)
        return

    # PRIORITET:
    # 1. covek
    if people_conf:
        template_id = TPL_PERSON
        confidence = max(people_conf)
    # 2. pas/macka
    elif animal_conf:
        template_id = TPL_ANIMAL
        confidence = max(animal_conf)
    # 3. ptica
    elif bird_conf:
        template_id = TPL_BIRD
        confidence = max(bird_conf)
    # 4. zelenilo
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
        print("greska slanja u middleware:", e)


@app.route("/bvms-event", methods=["POST"])
def bvms_event():
    data = request.get_json(force=True)
    cam_name = data.get("camera")
    if not cam_name:
        return jsonify({"error": "camera missing"}), 400

    rtsp = CAMERA_RTSP_MAP.get(cam_name)
    if not rtsp:
        return jsonify({"error": "unknown camera"}), 400

    # dozvoljavamo da klijent kaze koliko da gleda
    duration = data.get("duration", DEFAULT_DURATION)

    analyze_camera(rtsp, cam_name, duration_sec=duration)
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)


