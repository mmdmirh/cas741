#!/usr/bin/env python3
"""
FitCoachAR — Interface Enforcement Demo
========================================

This script demonstrates that Python ABCs (Abstract Base Classes) enforce
interface contracts — exactly like Java's ``interface`` keyword.

Run:
    python test_interfaces.py

What You'll See:
    ✓  Concrete implementations can be instantiated
    ✗  Abstract interfaces CANNOT be instantiated → TypeError
"""

import sys
import os

# Ensure the backend root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from modules.m3_video_formatting import IVideoFormatter, Base64VideoFormatter
from modules.m5_kinematic_engine import IKinematicEngine, KinematicEngine
from modules.m8_signal_smoothing import ISignalSmoother, KalmanSmoother

PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"
DIVIDER = "─" * 60


def test_interface_cannot_be_instantiated():
    """ABC interfaces raise TypeError if you try to create an instance."""
    print(f"\n{DIVIDER}")
    print("TEST 1: Attempting to instantiate ABSTRACT interfaces")
    print(f"{DIVIDER}")

    interfaces = [
        ("IVideoFormatter",   IVideoFormatter),
        ("IKinematicEngine",  IKinematicEngine),
        ("ISignalSmoother",   ISignalSmoother),
    ]

    all_passed = True
    for name, cls in interfaces:
        try:
            obj = cls()  # This SHOULD raise TypeError
            print(f"  {FAIL}  {name}() — unexpectedly succeeded!")
            all_passed = False
        except TypeError as e:
            print(f"  {PASS}  {name}() → TypeError: {e}")

    return all_passed


def test_concrete_classes_work():
    """Concrete implementations CAN be instantiated and used."""
    print(f"\n{DIVIDER}")
    print("TEST 2: Concrete implementations work correctly")
    print(f"{DIVIDER}")

    all_passed = True

    # M5: KinematicEngine
    try:
        engine = KinematicEngine()
        p1 = np.array([1.0, 0.0, 0.0])
        p2 = np.array([0.0, 0.0, 0.0])  # Joint
        p3 = np.array([0.0, 1.0, 0.0])
        angle = engine.compute_joint_angle(p1, p2, p3)
        assert abs(angle - 90.0) < 0.01, f"Expected 90°, got {angle}°"
        print(f"  {PASS}  KinematicEngine.compute_joint_angle([1,0,0], [0,0,0], [0,1,0]) = {angle:.1f}°")
    except Exception as e:
        print(f"  {FAIL}  KinematicEngine — {e}")
        all_passed = False

    # M8: KalmanSmoother
    try:
        smoother = KalmanSmoother()
        raw_values = [10.0, 12.0, 11.0, 13.0, 10.5]
        smoothed = [smoother.smooth(v) for v in raw_values]
        print(f"  {PASS}  KalmanSmoother: {raw_values} → {[f'{v:.2f}' for v in smoothed]}")
    except Exception as e:
        print(f"  {FAIL}  KalmanSmoother — {e}")
        all_passed = False

    # M3: Base64VideoFormatter
    try:
        formatter = Base64VideoFormatter()
        result = formatter.decode_frame("invalid data")
        assert result is None
        print(f"  {PASS}  Base64VideoFormatter.decode_frame('invalid data') → None")
    except Exception as e:
        print(f"  {FAIL}  Base64VideoFormatter — {e}")
        all_passed = False

    return all_passed


def test_isinstance_check():
    """Concrete classes are proper subtypes of their interfaces."""
    print(f"\n{DIVIDER}")
    print("TEST 3: isinstance() confirms interface inheritance")
    print(f"{DIVIDER}")

    all_passed = True

    checks = [
        (KinematicEngine(), IKinematicEngine, "KinematicEngine", "IKinematicEngine"),
        (KalmanSmoother(),  ISignalSmoother,  "KalmanSmoother",  "ISignalSmoother"),
        (Base64VideoFormatter(), IVideoFormatter, "Base64VideoFormatter", "IVideoFormatter"),
    ]

    for obj, iface, obj_name, iface_name in checks:
        result = isinstance(obj, iface)
        if result:
            print(f"  {PASS}  isinstance({obj_name}, {iface_name}) → True")
        else:
            print(f"  {FAIL}  isinstance({obj_name}, {iface_name}) → False")
            all_passed = False

    return all_passed


if __name__ == "__main__":
    print("\n" + "═" * 60)
    print("  FitCoachAR — ABC Interface Enforcement Demo")
    print("  Python's abc.ABC ≡ Java's interface keyword")
    print("═" * 60)

    results = [
        test_interface_cannot_be_instantiated(),
        test_concrete_classes_work(),
        test_isinstance_check(),
    ]

    print(f"\n{DIVIDER}")
    if all(results):
        print(f"  {PASS}  ALL TESTS PASSED — Interface contracts enforced!")
    else:
        print(f"  {FAIL}  Some tests failed")
    print(DIVIDER + "\n")
