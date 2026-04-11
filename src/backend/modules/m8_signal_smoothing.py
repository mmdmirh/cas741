"""
M8 — Signal Smoothing Module
==============================

MG Classification : Software Decision
Secret            : Choice of smoothing algorithm (Kalman, Savitzky-Golay)
                    and its tuning parameters.
Service           : Reduces high-frequency noise in joint angle time-series
                    and landmark coordinate streams to provide stable
                    inputs for downstream modules (M5, M6).

MIS Syntax
----------
  smooth(value: float)                    → float
  smooth_landmarks(landmarks: List[LM])  → List[LM]

MIS Semantics
-------------
  State Variables : Internal filter state (estimate, error covariance for
                    Kalman; rolling window for Savitzky-Golay)
  Assumptions     : Measurements arrive at a roughly constant sample rate.
  Transitions     : Each call updates the internal state and returns the
                    filtered output.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, List

import numpy as np
from scipy.signal import savgol_filter


# ═══════════════════════════════════════════════════════════════════════════════
#  I N T E R F A C E S
# ═══════════════════════════════════════════════════════════════════════════════

class ISignalSmoother(ABC):
    """Abstract interface for scalar signal smoothing."""
    @abstractmethod
    def smooth(self, value: float) -> float:
        ...


class ILandmarkSmoother(ABC):
    """Abstract interface for multi-landmark spatial smoothing."""
    @abstractmethod
    def smooth_landmarks(self, landmarks: List[Any]) -> List[Any]:
        ...


# ═══════════════════════════════════════════════════════════════════════════════
#  C O N C R E T E   I M P L E M E N T A T I O N S
# ═══════════════════════════════════════════════════════════════════════════════


class KalmanSmoother(ISignalSmoother):
    """1-D Kalman filter for scalar angle smoothing."""
    def __init__(self, process_variance: float = 0.01,
                 measurement_variance: float = 0.1):
        self.process_variance = process_variance
        self.measurement_variance = measurement_variance
        self.estimate = 0.0
        self.error_covariance = 1.0
        self.is_initialized = False

    def smooth(self, value: float) -> float:
        if not self.is_initialized:
            self.estimate = value
            self.is_initialized = True
            return self.estimate

        # Prediction phase
        prediction = self.estimate
        prediction_error_covariance = self.error_covariance + self.process_variance

        # Update phase
        kalman_gain = prediction_error_covariance / (prediction_error_covariance + self.measurement_variance)
        self.estimate = prediction + kalman_gain * (value - prediction)
        self.error_covariance = (1 - kalman_gain) * prediction_error_covariance

        return self.estimate


class KalmanLandmarkSmootherAdapter(ILandmarkSmoother):
    """Applies per-coordinate Kalman filtering to a full landmark set."""
    def __init__(self):
        self.disabled = os.getenv("FIT3D_RAW_LANDMARKS", "0") == "1"
        self.filters_x = {}
        self.filters_y = {}
        self.filters_z = {}

    def smooth_landmarks(self, landmarks: List[Any]) -> List[Any]:
        if not landmarks:
            return []

        if self.disabled:
             return landmarks

        smoothed_landmarks = []
        for i, lm in enumerate(landmarks):
            if i not in self.filters_x:
                self.filters_x[i] = KalmanSmoother()
                self.filters_y[i] = KalmanSmoother()
                self.filters_z[i] = KalmanSmoother()

            sx = self.filters_x[i].smooth(lm.x)
            sy = self.filters_y[i].smooth(lm.y)
            sz = self.filters_z[i].smooth(lm.z)

            class SmoothedLandmark:
                def __init__(self, x, y, z, visibility):
                    self.x = x
                    self.y = y
                    self.z = z
                    self.visibility = visibility

            smoothed_landmarks.append(SmoothedLandmark(sx, sy, sz, lm.visibility))

        return smoothed_landmarks


class LandmarkSmoother(ILandmarkSmoother):
    """Uses Savitzky-Golay filtering to smooth landmark trajectories."""
    def __init__(self, window_length=5, polyorder=2):
        self.disabled = os.getenv("FIT3D_RAW_LANDMARKS", "0") == "1"
        self.window_length = window_length
        self.polyorder = polyorder
        self.history = {}

    def smooth_landmarks(self, landmarks: List[Any]) -> List[Any]:
        if not landmarks:
            return []
        
        if self.disabled:
            return landmarks
            
        for i, lm in enumerate(landmarks):
            if i not in self.history:
                self.history[i] = []
            self.history[i].append([lm.x, lm.y, lm.z, lm.visibility])

        if len(next(iter(self.history.values()))) > self.window_length:
            for i in self.history:
                self.history[i].pop(0)

        if len(next(iter(self.history.values()))) < self.window_length:
            return landmarks

        smoothed_landmarks = []
        for i, history_queue in self.history.items():
            history_array = np.array(history_queue)
            
            smoothed_x = savgol_filter(history_array[:, 0], self.window_length, self.polyorder)[-1]
            smoothed_y = savgol_filter(history_array[:, 1], self.window_length, self.polyorder)[-1]
            smoothed_z = savgol_filter(history_array[:, 2], self.window_length, self.polyorder)[-1]
            current_visibility = history_array[-1, 3]

            class SmoothedLandmark:
                def __init__(self, x, y, z, visibility):
                    self.x = x
                    self.y = y
                    self.z = z
                    self.visibility = visibility

            smoothed_landmarks.append(SmoothedLandmark(smoothed_x, smoothed_y, smoothed_z, current_visibility))

        return smoothed_landmarks
