"""
M5 — Kinematic Engine Module
==============================

MG Classification : Software Decision
Secret            : Vector math formulas for angle computation and
                    coordinate transforms.
Service           : Translates raw 2D/3D landmarks into absolute joint
                    angles and normalised form-quality metrics.

MIS Syntax
----------
  compute_joint_angle(p1, p2, p3)              → float   (degrees)
  extract_metrics(landmarks, exercise_type)    → dict    {primary, form: {...}}

MIS Semantics
-------------
  State Variables : None (pure computation)
  Assumptions     : Landmark coordinates are ordered per M4 output; at least
                    3 non-collinear points for angle computation.
  Transitions     : Stateless — same inputs always produce the same outputs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

import numpy as np


# ═══════════════════════════════════════════════════════════════════════════════
#  I N T E R F A C E  (like Java's  interface IKinematicEngine)
# ═══════════════════════════════════════════════════════════════════════════════

class IKinematicEngine(ABC):
    """Abstract interface for kinematic feature extraction.

    Defines the contract for computing joint angles and biomechanical
    metrics from pose landmarks.

    Java equivalent:
        public interface IKinematicEngine {
            double computeJointAngle(Point3D p1, Point3D p2, Point3D p3);
            Map<String, Object> extractMetrics(List<Landmark> landmarks,
                                               String exerciseType);
        }
    """

    @abstractmethod
    def compute_joint_angle(
        self,
        p1: np.ndarray,
        p2: np.ndarray,
        p3: np.ndarray,
    ) -> float:
        """Compute the angle at joint *p2* formed by the segments p1–p2–p3.

        Parameters
        ----------
        p1, p2, p3 : numpy.ndarray
            2D or 3D coordinates of three body landmarks.

        Returns
        -------
        float
            Angle in degrees ∈ [0, 180].
        """
        ...

    @abstractmethod
    def extract_metrics(
        self,
        landmarks: List[Dict[str, float]],
        landmark_dict: Dict[str, int],
        exercise_type: str,
    ) -> Dict[str, Any]:
        """Extract the primary angle and form-quality features.

        Returns
        -------
        dict
            ``{"primary": float, "form": {"feature_name": float, ...}}``
        """
        ...


# ═══════════════════════════════════════════════════════════════════════════════
#  C O N C R E T E   I M P L E M E N T A T I O N
# ═══════════════════════════════════════════════════════════════════════════════

class KinematicEngine(IKinematicEngine):
    """Concrete kinematic engine using 3-point vector angle computation.

    The *secret* hidden by this module is the specific mathematical formula:
    the inverse-cosine of the dot-product of normalised limb vectors.

    This implementation delegates to the existing ``KinematicFeatureExtractor``
    from ``kinematics.py`` for exercise-specific metric bundles.
    """

    # ------ IKinematicEngine interface ------

    def compute_joint_angle(
        self,
        p1: np.ndarray,
        p2: np.ndarray,
        p3: np.ndarray,
    ) -> float:
        p1, p2, p3 = np.asarray(p1), np.asarray(p2), np.asarray(p3)
        ba = p1 - p2
        bc = p3 - p2
        norm_ba = np.linalg.norm(ba)
        norm_bc = np.linalg.norm(bc)
        if norm_ba < 1e-6 or norm_bc < 1e-6:
            return 0.0
        cosine = np.dot(ba, bc) / (norm_ba * norm_bc)
        return float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))

    def extract_metrics(
        self,
        landmarks: List[Dict[str, float]],
        landmark_dict: Dict[str, int],
        exercise_type: str,
    ) -> Dict[str, Any]:
        # Delegate to the existing battle-tested extractor
        from kinematics import KinematicFeatureExtractor
        return KinematicFeatureExtractor.extract_metrics(
            landmarks, landmark_dict, exercise_type
        )
