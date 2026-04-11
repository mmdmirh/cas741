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
  compute_angle(a, b, c)                       → float   (degrees)
  extract_metrics(landmarks, exercise)         → dict    {primary, form: {...}}

MIS Semantics
-------------
  State Variables : None (pure computation)
  Assumptions     : Landmark coordinates are ordered per M4 output; at least
                    3 non-collinear points for angle computation.
  Transitions     : Stateless — same inputs always produce the same outputs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

import numpy as np


# ═══════════════════════════════════════════════════════════════════════════════
#  I N T E R F A C E  (like Java's  interface IKinematicEngine)
# ═══════════════════════════════════════════════════════════════════════════════

class IKinematicEngine(ABC):
    """Abstract interface for kinematic feature extraction."""

    @abstractmethod
    def compute_angle(
        self,
        p1: np.ndarray,
        p2: np.ndarray,
        p3: np.ndarray,
    ) -> float:
        ...

    @abstractmethod
    def extract_metrics(
        self,
        landmarks: List[Any],
        landmark_dict: Dict[str, int],
        exercise_type: str,
    ) -> Dict[str, Any]:
        ...


# ═══════════════════════════════════════════════════════════════════════════════
#  C O N C R E T E   I M P L E M E N T A T I O N
# ═══════════════════════════════════════════════════════════════════════════════

class KinematicEngine(IKinematicEngine):
    """Concrete kinematic engine using 3-point vector angle computation."""

    def _get_coords(self, landmarks, idx) -> np.ndarray:
        lm = landmarks[idx]
        if isinstance(lm, dict):
            return np.array([lm["x"], lm["y"], lm.get("z", 0.0)])
        else:
            return np.array([getattr(lm, "x", 0.0), getattr(lm, "y", 0.0), getattr(lm, "z", 0.0)])

    def _compute_distance(self, p1: np.ndarray, p2: np.ndarray) -> float:
        return float(np.linalg.norm(p1 - p2))

    def compute_angle(
        self,
        p1: Any,
        p2: Any,
        p3: Any,
    ) -> float:
        a = np.asarray(p1)
        b = np.asarray(p2)
        c = np.asarray(p3)
        ba = a - b
        bc = c - b
        norm_ba = np.linalg.norm(ba)
        norm_bc = np.linalg.norm(bc)
        if norm_ba < 1e-6 or norm_bc < 1e-6:
            return 0.0
        cosine = np.dot(ba, bc) / (norm_ba * norm_bc)
        return float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))

    def compute_vertical_angle(self, p1: Any, p2: Any) -> float:
        vec = np.asarray(p2) - np.asarray(p1)
        norm = np.linalg.norm(vec)
        if norm < 1e-6: return 0.0
        vertical = np.array([0, 1, 0])
        cosine = np.dot(vec, vertical) / norm
        return float(np.degrees(np.arccos(np.abs(cosine))))

    def compute_angle_with_axis(self, joint_a, joint_b, axis):
        limb = np.array(joint_b) - np.array(joint_a)
        norm = np.linalg.norm(limb)
        if norm < 1e-6: return 0.0
        limb_norm = limb / norm
        cosine_angle = np.dot(limb_norm, axis)
        cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
        return float(np.degrees(np.arccos(cosine_angle)))

    def extract_metrics(
        self,
        landmarks: List[Any],
        landmark_dict: Dict[str, int],
        exercise_type: str,
    ) -> Dict[str, Any]:
        """Extract the primary angle and form-quality features."""
        try:
            l_shldr = self._get_coords(landmarks, landmark_dict["LEFT_SHOULDER"])
            r_shldr = self._get_coords(landmarks, landmark_dict["RIGHT_SHOULDER"])
            shoulder_width = self._compute_distance(l_shldr, r_shldr)
            scale = 1.0 / shoulder_width if shoulder_width > 0.01 else 1.0
        except (IndexError, KeyError):
            return {"primary": 0.0, "form": {}}

        ex = exercise_type.lower()
        metrics = {"primary": 0.0, "form": {}}

        if "curl" in ex:
            p = lambda name: self._get_coords(landmarks, landmark_dict[name])
            metrics["primary"] = self.compute_angle(
                p("RIGHT_SHOULDER"), p("RIGHT_ELBOW"), p("RIGHT_WRIST")
            )
            elbow_dist = self._compute_distance(p("RIGHT_SHOULDER"), p("RIGHT_ELBOW"))
            metrics["form"]["elbow_stability"] = elbow_dist * scale
            metrics["form"]["torso_swing"] = self.compute_vertical_angle(
                p("RIGHT_SHOULDER"), p("RIGHT_HIP")
            )

        elif "squat" in ex:
            p = lambda name: self._get_coords(landmarks, landmark_dict[name])
            metrics["primary"] = self.compute_angle(
                p("RIGHT_HIP"), p("RIGHT_KNEE"), p("RIGHT_ANKLE")
            )
            kw = self._compute_distance(p("LEFT_KNEE"), p("RIGHT_KNEE"))
            aw = self._compute_distance(p("LEFT_ANKLE"), p("RIGHT_ANKLE"))
            metrics["form"]["knee_valgus_index"] = kw / aw if aw > 0.01 else 1.0
            metrics["form"]["torso_lean"] = self.compute_vertical_angle(
                p("LEFT_HIP"), p("LEFT_SHOULDER")
            )
            metrics["form"]["hip_symmetry"] = abs(p("LEFT_HIP")[1] - p("RIGHT_HIP")[1]) * scale
            if scale > 0:
                sh_width = 1.0 / scale
                ank_width = self._compute_distance(p("LEFT_ANKLE"), p("RIGHT_ANKLE"))
                metrics["form"]["stance_width"] = ank_width / sh_width if sh_width > 0.01 else 0.0

        return metrics

    def extract_all_features(self, landmarks: List[Any], landmark_dict: Dict[str, int]) -> Dict[str, float]:
        """Provides the full angular feature set extraction (Active and Passive)."""
        features = {}

        def get_point(idx):
            return self._get_coords(landmarks, idx)

        # Active features
        features['left_elbow_angle'] = self.compute_angle(
            get_point(landmark_dict["LEFT_WRIST"]),
            get_point(landmark_dict["LEFT_ELBOW"]),
            get_point(landmark_dict["LEFT_SHOULDER"])
        )
        features['right_elbow_angle'] = self.compute_angle(
            get_point(landmark_dict["RIGHT_SHOULDER"]),
            get_point(landmark_dict["RIGHT_ELBOW"]),
            get_point(landmark_dict["RIGHT_WRIST"])
        )
        features['left_knee_angle'] = self.compute_angle(
            get_point(landmark_dict["LEFT_HIP"]),
            get_point(landmark_dict["LEFT_KNEE"]),
            get_point(landmark_dict["LEFT_ANKLE"])
        )
        features['right_knee_angle'] = self.compute_angle(
            get_point(landmark_dict["RIGHT_HIP"]),
            get_point(landmark_dict["RIGHT_KNEE"]),
            get_point(landmark_dict["RIGHT_ANKLE"])
        )

        left_hip = get_point(landmark_dict["LEFT_HIP"])
        right_hip = get_point(landmark_dict["RIGHT_HIP"])
        x_axis = right_hip - left_hip
        x_norm = np.linalg.norm(x_axis)
        x_axis = x_axis / x_norm if x_norm > 1e-6 else np.array([1, 0, 0])
        y_axis = np.array([0, -1, 0])
        z_axis = np.cross(x_axis, y_axis)
        z_norm = np.linalg.norm(z_axis)
        z_axis = z_axis / z_norm if z_norm > 1e-6 else np.array([0, 0, 1])
        y_axis = np.cross(z_axis, x_axis)

        features['left_shoulder_vertical_angle'] = self.compute_angle_with_axis(
            get_point(landmark_dict["LEFT_SHOULDER"]),
            get_point(landmark_dict["LEFT_ELBOW"]),
            y_axis
        )
        features['right_shoulder_vertical_angle'] = self.compute_angle_with_axis(
            get_point(landmark_dict["RIGHT_SHOULDER"]),
            get_point(landmark_dict["RIGHT_ELBOW"]),
            y_axis
        )

        # Passive features
        features['spine_angle'] = self.compute_angle(
            get_point(landmark_dict["LEFT_HIP"]),
            get_point(landmark_dict["LEFT_SHOULDER"]),
            get_point(landmark_dict["NOSE"])
        )
        features['hip_tilt'] = abs(left_hip[1] - right_hip[1]) * 100
        l_shldr = get_point(landmark_dict["LEFT_SHOULDER"])
        r_shldr = get_point(landmark_dict["RIGHT_SHOULDER"])
        features['shoulder_tilt'] = abs(l_shldr[1] - r_shldr[1]) * 100

        return features
