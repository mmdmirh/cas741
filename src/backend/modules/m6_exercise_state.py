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


# ═══════════════════════════════════════════════════════════════════════════════
#  D A T A   T Y P E S
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RepState:
    """Immutable snapshot of the exercise state machine."""
    rep_count: int = 0
    phase: str = "BOTTOM"
    progress: float = 0.0
    reached_top: bool = False


# ═══════════════════════════════════════════════════════════════════════════════
#  I N T E R F A C E  (like Java's  interface IExerciseStateMachine)
# ═══════════════════════════════════════════════════════════════════════════════

class IExerciseStateMachine(ABC):
    """Abstract interface for exercise repetition tracking.

    Java equivalent:
        public interface IExerciseStateMachine {
            RepState update(double metric, double timestamp);
            void reset();
        }
    """

    @abstractmethod
    def update(self, metric: float, timestamp: float) -> RepState:
        """Feed a new primary-angle sample and advance the state machine.

        Parameters
        ----------
        metric : float
            The current primary joint angle (degrees) from M5.
        timestamp : float
            Wall-clock timestamp in seconds.

        Returns
        -------
        RepState
            Current state including rep count, phase, and progress.
        """
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset the state machine to its initial state (zero reps)."""
        ...


# ═══════════════════════════════════════════════════════════════════════════════
#  C O N C R E T E   I M P L E M E N T A T I O N
# ═══════════════════════════════════════════════════════════════════════════════

class ExerciseStateMachine(IExerciseStateMachine):
    """Normalised rep counter driven by calibration parameters.

    The *secret* hidden by this module is the 4-phase state machine with
    hysteresis guards and timing constraints that prevent jitter-induced
    false positives.

    Wraps the existing ``NormalizedRepCounter`` from ``rep_counter_v2.py``.
    """

    def __init__(self, calibration_params):
        """
        Parameters
        ----------
        calibration_params : CalibrationParams
            Calibrated ROM (theta_low, theta_high) and timing (t_min, t_max).
        """
        from rep_counter_v2 import NormalizedRepCounter
        self._counter = NormalizedRepCounter(calibration_params)

    def update(self, metric: float, timestamp: float) -> RepState:
        state = self._counter.update(metric, timestamp)
        return RepState(
            rep_count=state.rep_count,
            phase=state.phase,
            progress=state.progress,
            reached_top=state.reached_top,
        )

    def reset(self) -> None:
        self._counter.reset()
