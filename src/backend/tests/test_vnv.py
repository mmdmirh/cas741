"""
FitCoachAR — V&V Test Suite
=============================

  T1: Perfect Squat (full rep cycle)
  T2: Failed Rep (insufficient depth)
  T4: State Machine Cycle (normalised progress)
  T5: Timing Constraint (too fast)
  T6: Intermediate State Transition (ascend)
  T7: State Reversal (failed transition)
  T8: Geometric Verification (angle accuracy)

Plus additional module-level tests:
  T_M5:  Kinematic Engine interface tests
  T_M8:  Signal Smoothing interface tests
  T_M3:  Video Formatter interface tests

Run:
    cd backend
    python3 -m pytest tests/test_vnv.py -v

Or without pytest:
    python3 tests/test_vnv.py
"""

import sys
import os
import math

# Ensure backend root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
from calibration_v2 import CalibrationParams
from modules.m6_exercise_state import ExerciseStateMachine as NormalizedRepCounter
from modules.m5_kinematic_engine import IKinematicEngine, KinematicEngine
from modules.m8_signal_smoothing import ISignalSmoother, KalmanSmoother
from modules.m3_video_formatting import IVideoFormatter, Base64VideoFormatter

# ═══════════════════════════════════════════════════════════════════════════════
#  H E L P E R S
# ═══════════════════════════════════════════════════════════════════════════════

def make_squat_params():
    """Default calibration for squats: 90° (bottom) to 180° (standing)."""
    return CalibrationParams(
        theta_low=90.0,
        theta_high=180.0,
        t_med=2.0,
        t_min=0.5,
        t_max=6.0,
    )

def make_curl_params():
    """Default calibration for bicep curls: 30° (contracted) to 160° (extended)."""
    return CalibrationParams(
        theta_low=30.0,
        theta_high=160.0,
        t_med=2.0,
        t_min=0.5,
        t_max=6.0,
    )

def generate_cosine_wave(low, high, n_points=60, n_reps=1):
    """Generate a smooth cosine wave simulating angle changes over time.
    
    Returns (angles, timestamps) where the wave goes high→low→high for each rep.
    """
    t = np.linspace(0, n_reps * 2.0, n_points)
    # Cosine wave: starts at high, dips to low, returns to high
    angles = (high + low) / 2 + (high - low) / 2 * np.cos(2 * np.pi * t / 2.0)
    return angles, t

PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"
DIVIDER = "─" * 65

results = []

def check(name, condition, detail=""):
    """Record a test result."""
    if condition:
        print(f"  {PASS}  {name}" + (f"  ({detail})" if detail else ""))
    else:
        print(f"  {FAIL}  {name}" + (f"  ({detail})" if detail else ""))
    results.append((name, condition))


# ═══════════════════════════════════════════════════════════════════════════════
#  T 1 :  P E R F E C T   S Q U A T
# ═══════════════════════════════════════════════════════════════════════════════

def test_T1_perfect_squat():
    """T1: Synthetic cosine wave 180°→90°→180° should produce exactly 1 rep."""
    print(f"\n{DIVIDER}")
    print("T1: Perfect Squat — Full valid repetition")
    print(DIVIDER)

    params = make_squat_params()
    counter = NormalizedRepCounter(params)

    angles, timestamps = generate_cosine_wave(
        low=params.theta_low, high=params.theta_high,
        n_points=60, n_reps=1,
    )

    for angle, t in zip(angles, timestamps):
        counter.update(angle, t)

    rep_count = counter.state.rep_count
    check("T1", rep_count == 1, f"RepCount={rep_count}, expected 1")


# ═══════════════════════════════════════════════════════════════════════════════
#  T 2 :  F A I L E D   R E P   (insufficient depth)
# ═══════════════════════════════════════════════════════════════════════════════

def test_T2_failed_rep():
    """T2: Angle dips to 100° only (never reaches 90° threshold) → no rep."""
    print(f"\n{DIVIDER}")
    print("T2: Failed Rep — Insufficient depth (100° only)")
    print(DIVIDER)

    params = make_squat_params()
    counter = NormalizedRepCounter(params)

    # Simulate: 180→100→180  (100 is above the 90° bottom threshold)
    angles, timestamps = generate_cosine_wave(
        low=100.0, high=params.theta_high,
        n_points=60, n_reps=1,
    )

    for angle, t in zip(angles, timestamps):
        counter.update(angle, t)

    rep_count = counter.state.rep_count
    check("T2", rep_count == 0, f"RepCount={rep_count}, expected 0 (depth insufficient)")


# ═══════════════════════════════════════════════════════════════════════════════
#  T 4 :  S T A T E   M A C H I N E   C Y C L E
# ═══════════════════════════════════════════════════════════════════════════════

def test_T4_state_machine_cycle():
    """T4: Trace every phase transition in a full rep cycle.
    
    Expected state machine path (from VnV Plan):
        BOTTOM → UP_PHASE → TOP → DOWN_PHASE → BOTTOM  (rep_count += 1)
    """
    print(f"\n{DIVIDER}")
    print("T4: State Machine Cycle — Phase-by-phase verification")
    print(DIVIDER)

    params = make_squat_params()  # theta_low=90, theta_high=180, t_min=0.5
    counter = NormalizedRepCounter(params)

    rom = params.theta_high - params.theta_low  # 90°

    # ── Phase 1: Start at BOTTOM (p < 0.15) ──
    counter.update(0.05 * rom + params.theta_low, 0.0)   # p=0.05 → angle=94.5°
    check("T4-phase1-BOTTOM", counter.state.phase == "BOTTOM",
          f"p=0.05 → phase={counter.state.phase}")

    # ── Phase 2: Move up past 0.15 threshold → UP_PHASE ──
    counter.update(0.20 * rom + params.theta_low, 0.3)   # p=0.20 → angle=108°
    counter.update(0.40 * rom + params.theta_low, 0.6)   # p=0.40 → angle=126°
    counter.update(0.60 * rom + params.theta_low, 0.9)   # p=0.60 → angle=144°
    check("T4-phase2-UP_PHASE", counter.state.phase == "UP_PHASE",
          f"p=0.60 → phase={counter.state.phase}")

    # ── Phase 3: Reach peak (p >= 0.85) → TOP ──
    counter.update(0.90 * rom + params.theta_low, 1.2)   # p=0.90 → angle=171°
    check("T4-phase3-TOP", counter.state.phase == "TOP",
          f"p=0.90 → phase={counter.state.phase}")

    # ── Phase 4: Start descending (p < 0.85, direction < 0) → DOWN_PHASE ──
    counter.update(0.70 * rom + params.theta_low, 1.5)   # p=0.70 → angle=153°
    check("T4-phase4-DOWN_PHASE", counter.state.phase == "DOWN_PHASE",
          f"p=0.70 → phase={counter.state.phase}")

    # ── Phase 5: Reach bottom again (p <= 0.15) → BOTTOM + rep counted ──
    counter.update(0.30 * rom + params.theta_low, 1.8)   # p=0.30 → angle=117°
    counter.update(0.10 * rom + params.theta_low, 2.1)   # p=0.10 → angle=99°

    state = counter.state
    check("T4-phase5-BOTTOM", state.phase == "BOTTOM",
          f"p=0.10 → phase={state.phase}")
    check("T4-rep-counted", state.rep_count == 1,
          f"RepCount={state.rep_count}, expected 1")



# ═══════════════════════════════════════════════════════════════════════════════
#  T 5 :  T I M I N G   C O N S T R A I N T   (too fast)
# ═══════════════════════════════════════════════════════════════════════════════

def test_T5_too_fast():
    """T5: Full ROM but dt=0.2s total (t_min=0.5s) → rep NOT counted."""
    print(f"\n{DIVIDER}")
    print("T5: Timing Constraint — Too fast (total < t_min)")
    print(DIVIDER)

    params = make_squat_params()  # t_min = 0.5s
    counter = NormalizedRepCounter(params)

    rom = params.theta_high - params.theta_low
    # Full ROM cycle but in only 0.2s total
    progress_sequence = [0.1, 0.9, 0.1]
    timestamps = [0.0, 0.1, 0.2]  # 0.2s total < t_min (0.5s)

    for p, t in zip(progress_sequence, timestamps):
        angle = p * rom + params.theta_low
        counter.update(angle, t)

    rep_count = counter.state.rep_count
    check("T5", rep_count == 0, f"RepCount={rep_count}, expected 0 (too fast)")


# ═══════════════════════════════════════════════════════════════════════════════
#  T 6 :  I N T E R M E D I A T E   S T A T E   (ascend)
# ═══════════════════════════════════════════════════════════════════════════════

def test_T6_intermediate_ascend():
    """T6: Progress 0.1→0.6 → state should transition to UP_PHASE (ascend)."""
    print(f"\n{DIVIDER}")
    print("T6: Intermediate State Transition — Ascend")
    print(DIVIDER)

    params = make_squat_params()
    counter = NormalizedRepCounter(params)

    rom = params.theta_high - params.theta_low

    # Start at bottom
    counter.update(params.theta_low + 0.1 * rom, 0.0)
    # Move to p=0.6 (mid-range, ascending)
    for i in range(1, 6):
        p = 0.1 + i * 0.1  # 0.2, 0.3, 0.4, 0.5, 0.6
        counter.update(p * rom + params.theta_low, i * 0.3)

    state = counter.state
    check("T6", state.phase == "UP_PHASE", f"Phase={state.phase}, expected UP_PHASE")
    check("T6-no-rep", state.rep_count == 0, f"RepCount={state.rep_count}, expected 0")


# ═══════════════════════════════════════════════════════════════════════════════
#  T 7 :  S T A T E   R E V E R S A L
# ═══════════════════════════════════════════════════════════════════════════════

def test_T7_state_reversal():
    """T7: Progress 0.1→0.6→0.1 (goes up then back down) → no rep, back to BOTTOM."""
    print(f"\n{DIVIDER}")
    print("T7: State Reversal — Failed transition")
    print(DIVIDER)

    params = make_squat_params()
    counter = NormalizedRepCounter(params)

    rom = params.theta_high - params.theta_low

    # Bottom → ascending to 0.6 → reverse back to 0.1
    progress_seq = [0.05, 0.2, 0.4, 0.6, 0.4, 0.2, 0.05]
    for i, p in enumerate(progress_seq):
        counter.update(p * rom + params.theta_low, i * 0.3)

    state = counter.state
    check("T7", state.phase == "BOTTOM", f"Phase={state.phase}, expected BOTTOM")
    check("T7-no-rep", state.rep_count == 0, f"RepCount={state.rep_count}, expected 0")


# ═══════════════════════════════════════════════════════════════════════════════
#  T 8 :  G E O M E T R I C   V E R I F I C A T I O N
# ═══════════════════════════════════════════════════════════════════════════════

def test_T8_geometric_accuracy():
    """T8: Verify angle calculation accuracy against known geometric cases."""
    print(f"\n{DIVIDER}")
    print("T8: Geometric Verification — Known angle computations")
    print(DIVIDER)

    engine = KinematicEngine()

    # Case 1: Right angle (90°)
    p1 = np.array([1.0, 0.0, 0.0])
    p2 = np.array([0.0, 0.0, 0.0])
    p3 = np.array([0.0, 1.0, 0.0])
    angle = engine.compute_angle(p1, p2, p3)
    check("T8a-90°", abs(angle - 90.0) < 0.1, f"angle={angle:.2f}°")

    # Case 2: Straight (180°)
    p1 = np.array([1.0, 0.0, 0.0])
    p2 = np.array([0.0, 0.0, 0.0])
    p3 = np.array([-1.0, 0.0, 0.0])
    angle = engine.compute_angle(p1, p2, p3)
    check("T8b-180°", abs(angle - 180.0) < 0.1, f"angle={angle:.2f}°")

    # Case 3: Acute (45°)
    p1 = np.array([1.0, 0.0, 0.0])
    p2 = np.array([0.0, 0.0, 0.0])
    p3 = np.array([1.0, 1.0, 0.0])
    angle = engine.compute_angle(p1, p2, p3)
    check("T8c-45°", abs(angle - 45.0) < 0.1, f"angle={angle:.2f}°")

    # Case 4: Obtuse (120°)
    p1 = np.array([1.0, 0.0, 0.0])
    p2 = np.array([0.0, 0.0, 0.0])
    p3 = np.array([-0.5, math.sqrt(3)/2, 0.0])
    angle = engine.compute_angle(p1, p2, p3)
    check("T8d-120°", abs(angle - 120.0) < 0.1, f"angle={angle:.2f}°")

    # Case 5: 3D angle (60°)
    p1 = np.array([1.0, 0.0, 0.0])
    p2 = np.array([0.0, 0.0, 0.0])
    p3 = np.array([0.5, math.sqrt(3)/2, 0.0])
    angle = engine.compute_angle(p1, p2, p3)
    check("T8e-60°", abs(angle - 60.0) < 0.1, f"angle={angle:.2f}°")


# ═══════════════════════════════════════════════════════════════════════════════
#  T _ M 5 :  K I N E M A T I C   E N G I N E   I N T E R F A C E
# ═══════════════════════════════════════════════════════════════════════════════

def test_M5_interface():
    """Module M5: KinematicEngine properly implements IKinematicEngine."""
    print(f"\n{DIVIDER}")
    print("T_M5: Kinematic Engine — Interface compliance")
    print(DIVIDER)

    engine = KinematicEngine()
    check("M5-isinstance", isinstance(engine, IKinematicEngine))

    try:
        IKinematicEngine()
        check("M5-abc-enforced", False, "Should have raised TypeError")
    except TypeError:
        check("M5-abc-enforced", True, "Cannot instantiate interface directly")


# ═══════════════════════════════════════════════════════════════════════════════
#  T _ M 8 :  S I G N A L   S M O O T H I N G
# ═══════════════════════════════════════════════════════════════════════════════

def test_M8_smoothing():
    """Module M8: Kalman smoother reduces noise."""
    print(f"\n{DIVIDER}")
    print("T_M8: Signal Smoothing — Noise reduction")
    print(DIVIDER)

    smoother = KalmanSmoother()
    check("M8-isinstance", isinstance(smoother, ISignalSmoother))

    # Feed noisy 90° signal
    noisy = [90.0 + np.random.normal(0, 5) for _ in range(20)]
    smoothed = [smoother.smooth(v) for v in noisy]

    # Smoothed values should have lower variance
    raw_std = np.std(noisy)
    smooth_std = np.std(smoothed[5:])  # skip initial transient
    check("M8-reduces-noise", smooth_std < raw_std,
          f"raw_std={raw_std:.2f}, smoothed_std={smooth_std:.2f}")


# ═══════════════════════════════════════════════════════════════════════════════
#  T _ M 3 :  V I D E O   F O R M A T T E R
# ═══════════════════════════════════════════════════════════════════════════════

def test_M3_formatter():
    """Module M3: Video formatter rejects invalid data and accepts valid JPEG."""
    print(f"\n{DIVIDER}")
    print("T_M3: Video Formatter — Decode validation")
    print(DIVIDER)

    fmt = Base64VideoFormatter()
    check("M3-isinstance", isinstance(fmt, IVideoFormatter))

    # Must reject invalid input
    check("M3-reject-invalid", fmt.decode_frame("not a data uri") is None)
    check("M3-reject-empty", fmt.decode_frame("") is None)

    # Must reject malformed base64
    check("M3-reject-bad-b64",
          fmt.decode_frame("data:image/jpeg;base64,!!!notbase64!!!") is None)


# ═══════════════════════════════════════════════════════════════════════════════
#  T _ M U L T I :  M U L T I P L E   R E P S
# ═══════════════════════════════════════════════════════════════════════════════

def test_multiple_reps():
    """Bonus: 5 clean reps should yield exactly 5 counted reps."""
    print(f"\n{DIVIDER}")
    print("T_MULTI: Multiple Reps — 5 clean squat reps")
    print(DIVIDER)

    params = make_squat_params()
    counter = NormalizedRepCounter(params)

    angles, timestamps = generate_cosine_wave(
        low=params.theta_low, high=params.theta_high,
        n_points=300, n_reps=5,
    )

    for angle, t in zip(angles, timestamps):
        counter.update(angle, t)

    rep_count = counter.state.rep_count
    check("T_MULTI", rep_count == 5, f"RepCount={rep_count}, expected 5")


# ═══════════════════════════════════════════════════════════════════════════════
#  R U N N E R
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "═" * 65)
    print("  FitCoachAR — V&V Test Suite (from VnVPlan.tex)")
    print("═" * 65)

    test_T1_perfect_squat()
    test_T2_failed_rep()
    test_T4_state_machine_cycle()
    test_T5_too_fast()
    test_T6_intermediate_ascend()
    test_T7_state_reversal()
    test_T8_geometric_accuracy()
    test_M5_interface()
    test_M8_smoothing()
    test_M3_formatter()
    test_multiple_reps()

    # Summary
    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    failed = total - passed

    print(f"\n{'═' * 65}")
    if failed == 0:
        print(f"  {PASS}  ALL {total} TESTS PASSED")
    else:
        print(f"  {FAIL}  {passed}/{total} passed, {failed} FAILED:")
        for name, ok in results:
            if not ok:
                print(f"       ✗ {name}")
    print("═" * 65 + "\n")

    sys.exit(0 if failed == 0 else 1)
