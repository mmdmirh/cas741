import React, { useRef, useEffect } from 'react';

/**
 * AROverlay Component - Dynamic AR Visualization
 * 
 * Provides real-time visual feedback through:
 * - Skeleton rendering with colored joints
 * - Target "shadow" poses for alignment
 * - Directional arrows pointing to ideal positions
 * - Colored angle sectors (green = correct, red = error)
 * 
 * Based on FitCoachAR proposal Section 4.4
 */
const MEDIAPIPE_CONNECTIONS = [
  [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
  [11, 23], [12, 24], [23, 24],
  [23, 25], [25, 27], [27, 29], [27, 31],
  [24, 26], [26, 28], [28, 30], [28, 32],
];

const MOVENET_CONNECTIONS = [
  [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],
  [5, 11], [6, 12], [11, 12],
  [11, 13], [13, 15],
  [12, 14], [14, 16],
  [0, 1], [0, 2], [1, 3], [2, 4],
];

const MEDIAPIPE_JOINTS = {
  rightElbow: 14,
  rightKnee: 26,
};

const MOVENET_JOINTS = {
  rightElbow: 8,
  rightKnee: 14,
};

export default function AROverlay({
  landmarks,
  feedbackLandmarks = [],
  arrowFeedback = [],  // New: structured arrow data from backend
  selectedExercise,
  targetAngles = {},
  currentAngles = {},
  backend
}) {
  const canvasRef = useRef(null);

  const backendKey = backend && backend.startsWith('movenet') ? 'movenet' : 'mediapipe';
  const connections = backendKey === 'movenet' ? MOVENET_CONNECTIONS : MEDIAPIPE_CONNECTIONS;
  const joints = backendKey === 'movenet' ? MOVENET_JOINTS : MEDIAPIPE_JOINTS;
  const VISIBILITY_THRESHOLD = backendKey === 'movenet' ? 0.05 : 0.5;

  useEffect(() => {
    if (!canvasRef.current || !landmarks || landmarks.length === 0) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    // Mirror x to match the CSS scaleX(-1) on the video (selfie mode)
    const mx = (lm) => (1 - lm.x) * canvas.width;
    const my = (lm) => lm.y * canvas.height;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw skeleton connections
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
    ctx.lineWidth = 3;
    connections.forEach(([start, end]) => {
      const startLm = landmarks[start];
      const endLm = landmarks[end];
      if (startLm && endLm && startLm.visibility > VISIBILITY_THRESHOLD && endLm.visibility > VISIBILITY_THRESHOLD) {
        ctx.beginPath();
        ctx.moveTo(mx(startLm), my(startLm));
        ctx.lineTo(mx(endLm), my(endLm));
        ctx.stroke();
      }
    });

    // Draw landmarks with color-coded feedback
    landmarks.forEach((lm, index) => {
      if (lm.visibility < VISIBILITY_THRESHOLD) return;

      const x = mx(lm);
      const y = my(lm);

      // Check if this landmark has feedback
      const hasError = feedbackLandmarks.includes(index);

      ctx.beginPath();
      ctx.arc(x, y, 6, 0, 2 * Math.PI);
      ctx.fillStyle = hasError ? '#ef4444' : '#10b981'; // Red for error, green for good
      ctx.fill();
      ctx.strokeStyle = 'white';
      ctx.lineWidth = 2;
      ctx.stroke();
    });

    // Draw angle indicators for relevant joints
    const drawAngleIndicator = (centerIdx, angle, targetAngle, label) => {
      const lm = landmarks[centerIdx];
      if (!lm || lm.visibility < VISIBILITY_THRESHOLD) return;

      const x = mx(lm);
      const y = my(lm);

      const isCorrect = Math.abs(angle - targetAngle) < 15;
      const color = isCorrect ? '#10b981' : '#ef4444';
      const text = `${Math.round(angle)}°`;

      // Draw badge background
      ctx.font = 'bold 16px Inter, Arial';
      const textWidth = ctx.measureText(text).width;
      const padX = 8, padY = 4, badgeH = 24;
      const bx = x - (textWidth + padX * 2) / 2;
      const by = y - 30 - badgeH;

      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.roundRect(bx, by, textWidth + padX * 2, badgeH, 6);
      ctx.fill();

      // Draw text
      ctx.fillStyle = 'white';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(text, x, by + badgeH / 2);
      ctx.textAlign = 'left';
      ctx.textBaseline = 'alphabetic';
    };

    // Exercise-specific angle visualization
    if (selectedExercise === 'bicep_curls') {
      if (currentAngles.rightElbow !== undefined && targetAngles.rightElbow !== undefined) {
        drawAngleIndicator(joints.rightElbow, currentAngles.rightElbow, targetAngles.rightElbow, 'R Elbow');
      }
    } else if (selectedExercise === 'squats') {
      if (currentAngles.rightKnee !== undefined && targetAngles.rightKnee !== undefined) {
        drawAngleIndicator(joints.rightKnee, currentAngles.rightKnee, targetAngles.rightKnee, 'R Knee');
      }
    }

    // Draw directional arrows for correction guidance (using structured arrow data)
    // Mirror left/right directions since video is flipped
    const mirrorDirection = (dir) => {
      const map = { left: 'right', right: 'left', up_left: 'up_right', up_right: 'up_left', down_left: 'down_right', down_right: 'down_left' };
      return map[dir] || dir;
    };

    const drawArrow = (x, y, direction, color, size = 40) => {
      const directions = {
        up: { dx: 0, dy: -size },
        down: { dx: 0, dy: size },
        left: { dx: -size, dy: 0 },
        right: { dx: size, dy: 0 },
        up_left: { dx: -size * 0.7, dy: -size * 0.7 },
        up_right: { dx: size * 0.7, dy: -size * 0.7 },
        down_left: { dx: -size * 0.7, dy: size * 0.7 },
        down_right: { dx: size * 0.7, dy: size * 0.7 },
      };

      const dir = directions[direction] || { dx: 0, dy: -size };

      ctx.strokeStyle = color;
      ctx.fillStyle = color;
      ctx.lineWidth = 4;

      // Arrow shaft
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x + dir.dx, y + dir.dy);
      ctx.stroke();

      // Arrow head (larger, more visible)
      const headLength = 15;
      const angle = Math.atan2(dir.dy, dir.dx);
      ctx.beginPath();
      ctx.moveTo(x + dir.dx, y + dir.dy);
      ctx.lineTo(
        x + dir.dx - headLength * Math.cos(angle - Math.PI / 5),
        y + dir.dy - headLength * Math.sin(angle - Math.PI / 5)
      );
      ctx.lineTo(
        x + dir.dx - headLength * Math.cos(angle + Math.PI / 5),
        y + dir.dy - headLength * Math.sin(angle + Math.PI / 5)
      );
      ctx.closePath();
      ctx.fill();

      // Add glow effect for visibility
      ctx.shadowColor = color;
      ctx.shadowBlur = 10;
      ctx.stroke();
      ctx.shadowBlur = 0;
    };

    // Draw arrows from backend feedback
    arrowFeedback.forEach(arrow => {
      const lm = landmarks[arrow.joint_idx];
      if (!lm || lm.visibility < VISIBILITY_THRESHOLD) return;

      const x = mx(lm);
      const y = my(lm);

      drawArrow(x, y, mirrorDirection(arrow.direction), arrow.color || '#facc15', 45);
    });

  }, [landmarks, feedbackLandmarks, arrowFeedback, selectedExercise, targetAngles, currentAngles, backendKey]);


  return (
    <canvas
      ref={canvasRef}
      width={640}
      height={480}
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        zIndex: 2,
        pointerEvents: 'none'
      }}
    />
  );
}
