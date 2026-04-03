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

from abc import ABC, abstractmethod
from typing import Any, List

import numpy as np


# ═══════════════════════════════════════════════════════════════════════════════
#  I N T E R F A C E S
# ═══════════════════════════════════════════════════════════════════════════════

class ISignalSmoother(ABC):
    """Abstract interface for scalar signal smoothing.

    Java equivalent:
        public interface ISignalSmoother {
            double smooth(double rawValue);
        }
    """

    @abstractmethod
    def smooth(self, value: float) -> float:
        """Return a smoothed estimate given a new raw measurement.

        Parameters
        ----------
        value : float
            Raw sensor / angle measurement.

        Returns
        -------
        float
            Smoothed value.
        """
        ...


class ILandmarkSmoother(ABC):
    """Abstract interface for multi-landmark spatial smoothing.

    Java equivalent:
        public interface ILandmarkSmoother {
            List<Landmark> smoothLandmarks(List<Landmark> raw);
        }
    """

    @abstractmethod
    def smooth_landmarks(self, landmarks: List[Any]) -> List[Any]:
        """Smooth a full set of pose landmarks from one frame.

        Parameters
        ----------
        landmarks : list
            List of landmark objects with ``.x``, ``.y``, ``.z``,
            ``.visibility`` attributes.

        Returns
        -------
        list
            Smoothed landmark objects with the same interface.
        """
        ...


# ═══════════════════════════════════════════════════════════════════════════════
#  C O N C R E T E   I M P L E M E N T A T I O N S
# ═══════════════════════════════════════════════════════════════════════════════

class KalmanSmoother(ISignalSmoother):
    """1-D Kalman filter for scalar angle smoothing.

    The *secret* is the Kalman predict / update equations and their
    process/measurement variance tuning.

    Wraps ``SimpleKalmanFilter`` from ``filters.py``.
    """

    def __init__(self, process_variance: float = 0.01,
                 measurement_variance: float = 0.1):
        from filters import SimpleKalmanFilter
        self._filter = SimpleKalmanFilter(process_variance, measurement_variance)

    def smooth(self, value: float) -> float:
        return self._filter.update(value)


class KalmanLandmarkSmootherAdapter(ILandmarkSmoother):
    """Applies per-coordinate Kalman filtering to a full landmark set.

    Wraps ``KalmanLandmarkSmoother`` from ``filters.py``.
    """

    def __init__(self):
        from filters import KalmanLandmarkSmoother
        self._smoother = KalmanLandmarkSmoother()

    def smooth_landmarks(self, landmarks: List[Any]) -> List[Any]:
        return self._smoother.smooth(landmarks)
