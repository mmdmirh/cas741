"""
M6 — Exercise State Machine Module
====================================

MG Classification : Behaviour Hiding
Secret            : Phase transition logic, hysteresis thresholds, and
                    timing constraints for repetition detection.
Service           : Tracks workout phases (Eccentric → Concentric) based
                    on real-time kinematic values to count reps and detect
                    incomplete or failed repetitions.

MIS Syntax
----------
  update(metric: float, timestamp: float)  → RepState
  reset()                                  → None

MIS Semantics
-------------
  State Variables : phase ∈ {BOTTOM, UP_PHASE, TOP, DOWN_PHASE}
                    rep_count ∈ ℕ₀
                    progress  ∈ [0.0, 1.0]
  Assumptions     : ``metric`` is the primary joint angle from M5.
                    ``timestamp`` is monotonically increasing (seconds).
  Transitions     : See state diagram in MG presentation slide 7.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


def _sign(x: float, eps: float = 1e-3) -> int:
    if x > eps: return 1
    if x < -eps: return -1
    return 0


# ═══════════════════════════════════════════════════════════════════════════════
#  D A T A   T Y P E S
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RepState:
    """Immutable snapshot of the exercise state machine."""
    rep_count: int = 0
    phase: str = "BOTTOM"
    reached_top: bool = False
    progress: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
#  I N T E R F A C E  (like Java's  interface IExerciseStateMachine)
# ═══════════════════════════════════════════════════════════════════════════════

class IExerciseStateMachine(ABC):
    """Abstract interface for exercise repetition tracking."""

    @abstractmethod
    def update(self, metric: float, timestamp: float) -> RepState:
        ...

    @abstractmethod
    def reset(self) -> None:
        ...


# ═══════════════════════════════════════════════════════════════════════════════
#  C O N C R E T E   I M P L E M E N T A T I O N
# ═══════════════════════════════════════════════════════════════════════════════

class ExerciseStateMachine(IExerciseStateMachine):
    """Normalised rep counter driven by calibration parameters.

    The *secret* hidden by this module is the 4-phase state machine with
    hysteresis guards and timing constraints that prevent jitter-induced
    false positives.
    """

    def __init__(self, calibration_params):
        """
        Parameters
        ----------
        calibration_params : CalibrationParams
            Calibrated ROM (theta_low, theta_high) and timing (t_min, t_max).
        """
        self.params = calibration_params
        self.state = RepState()
        self.t_start: Optional[float] = None
        self.last_metric: Optional[float] = None

    def reset(self) -> None:
        self.state = RepState()
        self.t_start = None
        self.last_metric = None

    def _progress(self, val: float) -> float:
        # Normalized progress 0.0 (Bottom) to 1.0 (Top)
        denom = max(1e-6, self.params.theta_high - self.params.theta_low)
        return (val - self.params.theta_low) / denom

    def update(self, metric: float, timestamp: float) -> RepState:
        p = self._progress(metric)
        self.state.progress = p

        last = self.last_metric if self.last_metric is not None else metric
        direction = _sign(metric - last)

        # Timeouts: If stuck in a phase too long, reset to start
        if self.t_start is not None:
            elapsed = timestamp - self.t_start
            if elapsed > self.params.t_max and self.state.phase != "BOTTOM":
                self.state.phase = "BOTTOM"
                self.t_start = None
                self.state.reached_top = False

        phase = self.state.phase

        # State Machine (Trough -> Peak -> Trough)
        if phase == "BOTTOM":
            # Moving UP (towards theta_high)
            if p > 0.15 and direction > 0:
                self.state.phase = "UP_PHASE"
                self.t_start = timestamp
                self.state.reached_top = False

        elif phase == "UP_PHASE":
            # Reached Top?
            if p >= 0.85:
                self.state.phase = "TOP"
                self.state.reached_top = True
            # Failed rep (went back down too early)
            elif p <= 0.1 and direction < 0:
                self.state.phase = "BOTTOM"
                self.t_start = None

        elif phase == "TOP":
            # Moving DOWN
            if p < 0.85 and direction < 0:
                self.state.phase = "DOWN_PHASE"

        elif phase == "DOWN_PHASE":
            # Reached Bottom (Rep Complete)
            if p <= 0.15:
                if self.state.reached_top and self.t_start is not None:
                    duration = timestamp - self.t_start
                    # Minimal sanity check on duration
                    if duration >= self.params.t_min:
                        self.state.rep_count += 1

                self.state.phase = "BOTTOM"
                self.t_start = None
                self.state.reached_top = False

        self.last_metric = metric
        return RepState(
            rep_count=self.state.rep_count,
            phase=self.state.phase,
            progress=self.state.progress,
            reached_top=self.state.reached_top
        )
