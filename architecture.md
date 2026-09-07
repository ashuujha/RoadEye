# System architecture

## Stack
Python 3.11, FastAPI/Uvicorn, SQLite, NumPy, OpenCV, PyTorch/torchvision CPU, EasyOCR (`gpu=False`), Ultralytics YOLOv8n, and plain HTML/JavaScript with Leaflet assets. This minimizes DevOps and keeps CV support strong. CityFlow baseline tracks are preferred; a generic ResNet fallback is explicitly labeled if vehicle-specialized weights cannot be exported.

```mermaid
flowchart TD
 C[CityFlow videos metadata tracks] --> I[Audit/import]
 I --> T[Predicted tracklets/evidence]
 T --> E[CPU appearance embeddings]
 T --> O[Optional OCR]
 E --> A[Predicted cross-camera association]
 O --> A
 P[Indian plate images] --> N[CPU detector + OCR]
 A --> D[(SQLite predictions)]
 N --> D
 D --> F[FastAPI]
 F --> U[Test frontend map/replay/analytics]
 G[Held-out labels] --> V[Offline evaluator]
 A --> V
 N --> V
 J[Optional Colab job] --> B[Weights/embeddings/results bundle]
 B --> E
```

Use synchronized scenario-relative timestamps, GPS camera points, and straight-line inferred links. Appearance similarity is primary; normalized OCR edit similarity is secondary only when both reads are legible. Reject ambiguous links. Analytics count observed visits, not interpolated points or total city traffic. Store provenance, model versions, frame paths, boxes, score types, and run IDs; keep evaluator identities separate.

Future-only architecture sections: Kafka streaming, road-network matching, and authenticated access/retention/misuse governance. None is implemented in this hackathon build.

