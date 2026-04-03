"""
FitCoachAR — Module Package
============================

This package organises the backend into the 8-module hierarchy described in
the Module Guide (MG) and Module Interface Specification (MIS).

Module Hierarchy (Parnas Information Hiding):
─────────────────────────────────────────────
  Hardware Hiding        │  M1  Video Input  (frontend — browser getUserMedia)
                         │  M2  Display Output  (frontend — AROverlay.jsx)
  ─────────────────────────────────────────────
  Behaviour Hiding       │  M3  Video Stream Formatting
                         │  M6  Exercise State Machine
                         │  M7  UI Rendering  (api/ — Django consumers & views)
  ─────────────────────────────────────────────
  Software Decision      │  M4  Pose Tracking  (ML backend selection)
                         │  M5  Kinematic Engine  (angle computation)
                         │  M8  Signal Smoothing  (Kalman / Savitzky-Golay)

Each sub-module exposes:
  • An **interface** (Python ABC) defining the contract (MIS Syntax)
  • One or more **concrete implementations** hiding the secret (MIS Semantics)

Python's ``abc.ABC`` + ``@abstractmethod`` is equivalent to Java's ``interface``
keyword — subclasses that fail to implement all abstract methods will raise
``TypeError`` at instantiation time.
"""

# Re-export all interfaces for convenient top-level access
from modules.m3_video_formatting import IVideoFormatter, Base64VideoFormatter
from modules.m4_pose_tracking import IPoseTracker, IPoseEstimator
from modules.m5_kinematic_engine import IKinematicEngine, KinematicEngine
from modules.m6_exercise_state import IExerciseStateMachine, ExerciseStateMachine
from modules.m8_signal_smoothing import ISignalSmoother, ILandmarkSmoother, KalmanSmoother, KalmanLandmarkSmootherAdapter

__all__ = [
    # Interfaces (ABC — like Java interfaces)
    "IVideoFormatter",
    "IPoseTracker",
    "IPoseEstimator",
    "IKinematicEngine",
    "IExerciseStateMachine",
    "ISignalSmoother",
    "ILandmarkSmoother",
    # Concrete Implementations
    "Base64VideoFormatter",
    "KinematicEngine",
    "ExerciseStateMachine",
    "KalmanSmoother",
    "KalmanLandmarkSmootherAdapter",
]
