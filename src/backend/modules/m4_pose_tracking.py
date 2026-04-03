"""
M4 — Pose Tracking Module
===========================

MG Classification : Software Decision
Secret            : Choice of ML tracker (MediaPipe, MoveNet, HRNet, etc.)
Service           : Converts a raw video frame into an array of 2D/3D
                    (x, y [, z]) landmarks with visibility scores.

MIS Syntax
----------
  estimate_pose(frame: ndarray) → Optional[List[Landmark]]
  landmark_dict()               → Dict[str, int]

MIS Semantics
-------------
  State Variables : Internal ML model weights (loaded once)
  Assumptions     : Input frame is a valid BGR numpy array with H, W ≥ 1
  Transitions     : Inference is stateless w.r.t. the model; may maintain
                    internal temporal buffers for smoothing.

Note
----
  The existing ``pose_backends/base.py`` already defines ``PoseBackend`` and
  ``PoseEstimator`` as ABCs.  This module re-exports them under the MG naming
  convention and provides a convenience alias so the module hierarchy is
  self-contained.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import numpy as np


# ═══════════════════════════════════════════════════════════════════════════════
#  I N T E R F A C E S  (re-exported from existing code)
# ═══════════════════════════════════════════════════════════════════════════════

class IPoseTracker(ABC):
    """Abstract interface for a full pose-processing backend.

    Equivalent to Java:
        public interface IPoseTracker {
            Map<String, Object> processFrame(Mat frameBGR);
            void close();
        }

    Existing implementations: MediaPipe2DBackend, MoveNet3DBackend, etc.
    """

    name: str = "base"
    dimension_hint: str = "2D"

    @abstractmethod
    def process_frame(self, frame_bgr: np.ndarray) -> Optional[Dict[str, Any]]:
        """Process a decoded BGR frame and return pose data payload."""
        ...

    def handle_command(self, command_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Dispatch external commands (calibration, reset, etc.)."""
        return None

    def close(self) -> None:
        """Release resources (model handles, GPU memory, etc.)."""
        return None


class IPoseEstimator(ABC):
    """Abstract interface for a standalone pose estimator.

    Lower-level than ``IPoseTracker`` — only returns raw landmarks without
    higher-level features like rep counting or feedback.
    """

    @abstractmethod
    def process_frame(self, frame_bgr: np.ndarray) -> Optional[Dict[str, Any]]:
        """Run inference on a single frame."""
        ...

    @abstractmethod
    def process_video(self, video_path: str) -> Optional[List[Dict[str, Any]]]:
        """Run inference on every frame of a video file."""
        ...

    @abstractmethod
    def landmark_dict(self) -> Dict[str, int]:
        """Return mapping from landmark name to index."""
        ...
