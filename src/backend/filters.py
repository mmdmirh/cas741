import os
import numpy as np
from scipy.signal import savgol_filter


class SimpleKalmanFilter:
    """A lightweight, 1D Kalman filter for smooth joint movement."""
    def __init__(self, process_variance=0.01, measurement_variance=0.1):
        self.process_variance = process_variance
        self.measurement_variance = measurement_variance
        self.estimate = 0.0
        self.error_covariance = 1.0
        self.is_initialized = False

    def update(self, measurement):
        if not self.is_initialized:
            self.estimate = measurement
            self.is_initialized = True
            return self.estimate

        # Prediction phase
        prediction = self.estimate
        prediction_error_covariance = self.error_covariance + self.process_variance

        # Update phase
        kalman_gain = prediction_error_covariance / (prediction_error_covariance + self.measurement_variance)
        self.estimate = prediction + kalman_gain * (measurement - prediction)
        self.error_covariance = (1 - kalman_gain) * prediction_error_covariance

        return self.estimate


class KalmanLandmarkSmoother:
    """Applies a Kalman filter to smooth landmark trajectories."""

    def __init__(self):
        # When FIT3D_RAW_LANDMARKS=1, bypass smoothing and return raw landmarks.
        self.disabled = os.getenv("FIT3D_RAW_LANDMARKS", "0") == "1"
        # Each landmark (x, y, z) gets its own filter
        self.filters_x = {}
        self.filters_y = {}
        self.filters_z = {}

    def smooth(self, landmarks):
        """Smooths a list of landmarks from a single frame."""
        if not landmarks:
            return []

        if self.disabled:
            # Return landmarks as-is (no temporal smoothing).
            return landmarks

        smoothed_landmarks = []
        for i, lm in enumerate(landmarks):
            if i not in self.filters_x:
                self.filters_x[i] = SimpleKalmanFilter()
                self.filters_y[i] = SimpleKalmanFilter()
                self.filters_z[i] = SimpleKalmanFilter()

            # Smooth each coordinate independently
            sx = self.filters_x[i].update(lm.x)
            sy = self.filters_y[i].update(lm.y)
            sz = self.filters_z[i].update(lm.z)

            # Create a new landmark object with the smoothed position
            class SmoothedLandmark:
                def __init__(self, x, y, z, visibility):
                    self.x = x
                    self.y = y
                    self.z = z
                    self.visibility = visibility

            smoothed_landmarks.append(SmoothedLandmark(sx, sy, sz, lm.visibility))

        return smoothed_landmarks



class LandmarkSmoother:
    """Uses Savitzky-Golay filtering to smooth landmark trajectories."""
    def __init__(self, window_length=5, polyorder=2):
        # When FIT3D_RAW_LANDMARKS=1, bypass smoothing and return raw landmarks.
        self.disabled = os.getenv("FIT3D_RAW_LANDMARKS", "0") == "1"
        self.window_length = window_length
        self.polyorder = polyorder
        self.history = {}

    def smooth(self, landmarks):
        """Smooths a list of landmarks from a single frame."""
        if not landmarks:
            return []

        if self.disabled:
            return landmarks

        # Add current landmarks to history
        for i, lm in enumerate(landmarks):
            if i not in self.history:
                self.history[i] = []
            self.history[i].append([lm.x, lm.y, lm.z, lm.visibility])

        # Ensure history is not longer than window length
        if len(next(iter(self.history.values()))) > self.window_length:
            for i in self.history:
                self.history[i].pop(0)
        
        # If we don't have enough history, return the raw landmarks
        if len(next(iter(self.history.values()))) < self.window_length:
            return landmarks

        smoothed_landmarks = []
        for i, history_queue in self.history.items():
            history_array = np.array(history_queue)
            
            # Smooth x, y, z coordinates
            smoothed_x = savgol_filter(history_array[:, 0], self.window_length, self.polyorder)[-1]
            smoothed_y = savgol_filter(history_array[:, 1], self.window_length, self.polyorder)[-1]
            smoothed_z = savgol_filter(history_array[:, 2], self.window_length, self.polyorder)[-1]
            
            # Use the most recent visibility score
            current_visibility = history_array[-1, 3]

            # Create a new landmark object (mimicking MediaPipe's structure)
            class SmoothedLandmark:
                def __init__(self, x, y, z, visibility):
                    self.x = x
                    self.y = y
                    self.z = z
                    self.visibility = visibility
            
            smoothed_landmarks.append(SmoothedLandmark(smoothed_x, smoothed_y, smoothed_z, current_visibility))

        return smoothed_landmarks
