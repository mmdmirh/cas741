# FitCoachAR — Source Code

This directory contains the implementation of FitCoachAR, an AR-based
exercise form coach. It is split into a Python backend (pose analysis,
state machine, persistence, LLM feedback) and a Vite/React frontend
(camera capture, skeleton overlay, UI).

The module naming under `backend/modules/` (M3–M6, M8) mirrors the Module
Guide (MG) in `docs/Design/SoftArchitecture/MG.pdf`. Modules M1 (Video
Input), M2 (Display Output) and M7 (UI Rendering) live in the frontend,
because their secrets are browser/OS concerns (webcam API, three.js
rendering, DOM).

## Layout

```
src/
├── backend/
│   ├── api/                 # Django views, URL routing, WebSocket consumer
│   ├── coaches/             # LLM + rule-based form feedback
│   ├── fitcoach_backend/    # Django ASGI project (settings, urls)
│   ├── modules/             # MG-aligned scientific computing modules
│   │   ├── m3_video_formatting.py
│   │   ├── m4_pose_tracking.py
│   │   ├── m5_kinematic_engine.py
│   │   ├── m6_exercise_state.py
│   │   └── m8_signal_smoothing.py
│   ├── scripts/             # Offline research / benchmarking (not part of
│   │                        # the live app)
│   ├── services/            # Standalone model services used by scripts/
│   ├── tests/               # pytest suite (VnV Report tests)
│   ├── calibration_v2.py    # Per-user calibration pipeline
│   ├── session.py           # Workout session bookkeeping
│   ├── main.py              # ASGI entrypoint shim
│   ├── manage.py            # Django management entry
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── AROverlay.jsx    # Skeleton rendering (M2)
    │   ├── Avatar.jsx
    │   └── main.jsx
    ├── public/
    ├── index.html
    ├── package.json
    └── vite.config.js
```

## Mapping to the Module Guide

| MG module | Secret | Where it lives |
| --- | --- | --- |
| M1 Video Input | Webcam capture API | Browser (`getUserMedia`, consumed in `frontend/src/App.jsx`) |
| M2 Display Output | Skeleton / badge rendering | `frontend/src/AROverlay.jsx` |
| M3 Video Formatting | Encode/decode for network transport | `backend/modules/m3_video_formatting.py` |
| M4 Pose Tracking | MediaPipe landmark inference | `backend/modules/m4_pose_tracking.py` |
| M5 Kinematic Engine | Vector-angle computation | `backend/modules/m5_kinematic_engine.py` |
| M6 Exercise State | FSM thresholds & rep counting | `backend/modules/m6_exercise_state.py` |
| M7 UI Rendering | WebSocket JSON schema + DOM updates | `frontend/src/App.jsx`, `frontend/src/main.jsx` |
| M8 Signal Smoothing | Kalman filter parameters | `backend/modules/m8_signal_smoothing.py` |

## Prerequisites

- **Python 3.10 or 3.11** (required by `mediapipe-silicon` and
  `channels`). Check with `python3 --version`.
- **Node.js 20+** and **npm 10+**. Check with `node --version`.
- A working **webcam**.
- macOS (Apple Silicon) or Linux. Windows users should substitute
  `mediapipe` for `mediapipe-silicon` in `backend/requirements.txt`.
- Optional: a **Cerebras Cloud** API key if you want live LLM coaching
  (`CEREBRAS_API_KEY`). The app runs without it; feedback will fall back
  to rule-based messages.

## Running locally

You need **two terminals**, one for the backend and one for the
frontend.

### 1. Backend — Django + Channels (ASGI)

```bash
cd src/backend

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# (Optional) enable LLM feedback
export CEREBRAS_API_KEY=sk-...

# Apply migrations (creates db.sqlite3 on first run)
python manage.py migrate

# Start the ASGI server on port 8000
daphne -b 127.0.0.1 -p 8000 fitcoach_backend.asgi:application
```

The backend now serves:

- REST API at `http://127.0.0.1:8000/api/v1/...`
- WebSocket at `ws://127.0.0.1:8000/ws` (pose streaming)

To verify it is up:

```bash
curl http://127.0.0.1:8000/
```

### 2. Frontend — Vite + React

In a second terminal:

```bash
cd src/frontend

# Install JS dependencies
npm install

# Start the dev server
npm run dev
```

Vite will print a local URL (typically `http://localhost:5173`). Open
it in a browser, grant camera permission, and the skeleton overlay
should appear.

### 3. Running the test suite

```bash
cd src/backend
source venv/bin/activate
pytest tests/
```

The tests in `tests/test_vnv.py` correspond to the system-test cases
(T1, T2, T4–T8) listed in the VnV Plan and executed in the VnV Report.

## Offline evaluation (optional)

The scripts under `backend/scripts/` are research tools used to
benchmark different pose backends (MediaPipe vs MotionBERT vs HRNet,
etc.) against the Fit3D dataset. They are **not required** to run the
app and are not part of the documented system.

If you want to run them, note that some scripts expect a MoveNet 3D
TFLite model; the `src/models/` folder that used to hold it has been
removed. Re-download the model and point the scripts at it via the
`--model` flag if needed.

## Troubleshooting

- **`mediapipe-silicon` fails to install on Linux/Windows.** Replace it
  with `mediapipe` in `requirements.txt`.
- **WebSocket connection refused.** Make sure the backend was started
  with `daphne` (ASGI), not `python manage.py runserver` — the stock
  Django dev server does not serve WebSockets.
- **Camera permission denied.** Check the browser's site settings; on
  macOS also check System Settings → Privacy & Security → Camera.
- **Port already in use.** Change the backend port via `daphne -p 8001
  ...` and update `VITE_BACKEND_URL` (or the hard-coded URL in
  `frontend/src/App.jsx`) accordingly.
