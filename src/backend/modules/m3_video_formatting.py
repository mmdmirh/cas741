"""
M3 — Video Stream Formatting Module
=====================================

MG Classification : Behaviour Hiding
Secret            : Frame encoding/decoding format (JPEG, base64, resolution)
Service           : Converts raw network data into decoded BGR image arrays
                    ready for downstream pose estimation.

MIS Syntax
----------
  decode_frame(raw_data: str) → numpy.ndarray[H, W, 3]   # BGR image

MIS Semantics
-------------
  State Variables : None (stateless transformation)
  Assumptions     : Input is a valid data-URI with MIME type image/jpeg
  Transitions     : Pure function — no side effects
"""

from __future__ import annotations

import base64
from abc import ABC, abstractmethod
from typing import Optional

import cv2
import numpy as np


# ═══════════════════════════════════════════════════════════════════════════════
#  I N T E R F A C E  (like Java's  interface IVideoFormatter)
# ═══════════════════════════════════════════════════════════════════════════════

class IVideoFormatter(ABC):
    """Abstract interface for video frame decoding.

    Any class that implements this interface MUST provide a ``decode_frame``
    method.  Attempting to instantiate ``IVideoFormatter`` directly will raise
    ``TypeError`` — exactly like Java's interface enforcement.
    """

    @abstractmethod
    def decode_frame(self, raw_data: str) -> Optional[np.ndarray]:
        """Decode a raw network payload into a BGR image array.

        Parameters
        ----------
        raw_data : str
            The raw string received over the WebSocket (e.g. a base64 data-URI).

        Returns
        -------
        numpy.ndarray or None
            Decoded BGR image of shape (H, W, 3), or ``None`` on failure.
        """
        ...


# ═══════════════════════════════════════════════════════════════════════════════
#  C O N C R E T E   I M P L E M E N T A T I O N
# ═══════════════════════════════════════════════════════════════════════════════

class Base64VideoFormatter(IVideoFormatter):
    """Decodes base64-encoded JPEG frames received over WebSocket.

    This is the *secret* hidden by M3: the specific wire format (base64 JPEG
    data-URI) is an implementation detail that callers never need to know.
    """

    EXPECTED_PREFIX = "data:image/jpeg;base64,"

    def decode_frame(self, raw_data: str) -> Optional[np.ndarray]:
        if not raw_data.startswith(self.EXPECTED_PREFIX):
            return None
        try:
            _, encoded = raw_data.split(",", 1)
            img_bytes = base64.b64decode(encoded)
            np_arr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            return frame
        except Exception:
            return None
