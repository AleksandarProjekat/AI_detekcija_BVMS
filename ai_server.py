### Ovaj server primi od skripte clientscript “CAM_WH_01”, uzme RTSP, pusti YOLO, odluci: ptice → 2, covek → 17 i posalje C# middleware-u.
# ai_server.py
from flask import Flask, request, jsonify
from ultralytics import YOLO
import cv2
import requests
from datetime import datetime

app = Flask(__name__)

model = YOLO("yolov8n.pt")  # mali model da radi na CPU

# mapiranje BVMS imena kamera na RTSP url
CAMERA_RTSP_MAP = {
    "CAM_WH_01": "rtsp://user:pass@192.168.1.51/stream1",
    "CAM_GATE_01": "rtsp://user:pass@192.168.1.52/stream1"
}

# tvoj C# middleware
MIDDLEWARE_URL = "http://192.168.1.100:5000/ai-event"  # promeni

def analyze_camera(rtsp_url, cam_name, duration=10):
    cap = cv2.VideoCapture(rtsp_url)
    start_time = datetime.utcnow()
    detections = []

    while (datetime.utcnow() - start_time).total_seconds() < duration:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.resize(frame, (640, 360))
        results = model(frame, verbose=False)

        for r in results:
            for b in r.boxes:
                cls_id = int(b.cls[0])
                cls_name = model.names[cls_id]
                conf = float(b.conf[0])

                if conf < 0.5:
                    continue

                if cls_name == "bird":
                    detections.append(("bird", 2, conf))
                elif cls_name == "person":
                    detections.append(("person", 17, conf))

    cap.release()

    if detections:
        # uzmi najjacu detekciju
        cls_name, template_id, confidence = max(detections, key=lambda x: x[2])
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
    else:
        print("Nista korisno na", cam_name)



@app.route("/bvms-event", methods=["POST"])
def bvms_event():
    data = request.get_json(force=True)
    cam_name = data.get("camera")
    if not cam_name:
        return jsonify({"error": "camera missing"}), 400

    rtsp = CAMERA_RTSP_MAP.get(cam_name)
    if not rtsp:
        return jsonify({"error": "unknown camera"}), 400

    analyze_camera(rtsp, cam_name)
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
