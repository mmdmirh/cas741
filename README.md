# FitCoachAR

**Author:** Seyedmohamad Mirhoseininejad (mirhos5@mcmaster.ca)
**Course:** CAS 741 --- Development of Scientific Computing Software
**Instructor:** Dr. Spencer Smith
**Term:** Winter 2026

FitCoachAR is a real-time, browser-based exercise form-feedback tool. It
uses a standard webcam plus a pre-trained pose-estimation backend
(MediaPipe Pose) to extract skeletal keypoints, computes joint angles
through a vector-based kinematic engine, and overlays a skeleton, rep
counter, and form-quality feedback on the live video via an AR canvas.
The project supports the squat and bicep curl as its initial exercises.

The project is a refactor of a monolithic CAS 772 prototype into an
eight-module, information-hiding decomposition (M1--M8) with abstract-base-class
interfaces and an automated pytest suite.

## Repository Layout

- `docs/` --- Documentation (SRS, VnV Plan, VnV Report, Module Guide,
  MIS, Reflect and Trace, Development Plan, plus Extras)
- `src/backend/` --- Python 3.9 backend (Django + Channels), pose
  pipeline, kinematic engine, state machine, Kalman smoother, tests
- `src/frontend/` --- React + Vite frontend with AR canvas overlay
- `refs/` --- Reference material and bibliography
- `.github/workflows/` --- CI for LaTeX builds and test runs

## Documentation Site

Compiled PDFs are published to GitHub Pages:

[https://mmdmirh.github.io/cas741/](https://mmdmirh.github.io/cas741/)

## Quick Start

Back-end:

```bash
cd src/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Front-end (separate terminal):

```bash
cd src/frontend
npm install
npm run dev
```

Open the Vite URL (typically `http://localhost:5173`) in a modern
browser, grant camera permission, pick an exercise, and begin.

Full installation and usage instructions are in
`docs/Extras/UserManual/UserManual.pdf`.

## License

MIT --- see [LICENSE](LICENSE).
