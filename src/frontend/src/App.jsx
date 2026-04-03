import React, { useState, useEffect, useRef, useCallback } from 'react';
import AROverlay from './AROverlay';
import './App.css';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

const EXERCISES = [
  { id: 'bicep_curls', label: 'Bicep Curls', icon: '💪', description: 'Track elbow angles and tempo for stronger curls.' },
  { id: 'squats', label: 'Squats', icon: '🏋️', description: 'Monitor depth and knee alignment for safer squats.' }
];

const SESSION_PRESETS = [
  { id: 'quick_squats', name: '3×10 Squats', sets: [{ exercise: 'squats', reps: 10 }, { exercise: 'squats', reps: 10 }, { exercise: 'squats', reps: 10 }] },
  { id: 'quick_curls', name: '3×12 Bicep Curls', sets: [{ exercise: 'bicep_curls', reps: 12 }, { exercise: 'bicep_curls', reps: 12 }, { exercise: 'bicep_curls', reps: 12 }] },
  { id: 'circuit', name: 'Circuit: Squats + Curls', sets: [{ exercise: 'squats', reps: 10 }, { exercise: 'bicep_curls', reps: 10 }, { exercise: 'squats', reps: 10 }, { exercise: 'bicep_curls', reps: 10 }] },
];

const CANONICAL_BASELINES = {
  bicep_curls: { extended: 160, contracted: 30 },
  squats: { up: 160, down: 50 },
};

const createDefaultSummary = () => ({
  records: [], active: { common: null, calibration: null }, critics: { common: 0.2 }
});

function App() {
  // ─── State ───────────────────────────────────────────────
  const [isMediaPipeReady, setIsMediaPipeReady] = useState(false);
  const [status, setStatus] = useState('Loading…');
  const [connectionState, setConnectionState] = useState('connecting'); // 'connected','connecting','disconnected'
  const [leftElbowAngle, setLeftElbowAngle] = useState(null);
  const [rightElbowAngle, setRightElbowAngle] = useState(null);
  const [leftKneeAngle, setLeftKneeAngle] = useState(null);
  const [rightKneeAngle, setRightKneeAngle] = useState(null);
  const [repCounter, setRepCounter] = useState(0);
  const repCounterRef = useRef(repCounter);
  const lastErrorRep = useRef(-1);
  const [errorReps, setErrorReps] = useState(0);
  const [repTimestamps, setRepTimestamps] = useState([]);
  const [feedbackMessage, setFeedbackMessage] = useState('');
  const [llmFeedback, setLlmFeedback] = useState('');
  const [feedbackLandmarks, setFeedbackLandmarks] = useState([]);
  const [arrowFeedback, setArrowFeedback] = useState([]);
  const [poseLandmarks, setPoseLandmarks] = useState([]);
  const [appState, setAppState] = useState('selection');
  const [sessionConfig, setSessionConfig] = useState([]);
  const [sessionProgress, setSessionProgress] = useState(null);
  const [sessionName, setSessionName] = useState('My Workout');
  const [workoutSummary, setWorkoutSummary] = useState(null);
  const workoutSummaryRef = useRef(workoutSummary);
  const [llmSummary, setLlmSummary] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isLlmLoading, setIsLlmLoading] = useState(false);
  const [formAnalysis, setFormAnalysis] = useState(null);
  const [formSnapshots, setFormSnapshots] = useState([]);
  const [postRepCommand, setPostRepCommand] = useState(null);
  const [selectedExercise, setSelectedExercise] = useState(null);
  const [countdown, setCountdown] = useState(null);
  const [latencyMs, setLatencyMs] = useState(null);
  const [roundTripMs, setRoundTripMs] = useState(null);
  const [backendName, setBackendName] = useState(null);
  const [appMode, setAppMode] = useState('common');
  const [calibrationSummary, setCalibrationSummary] = useState({});
  const [selectedRecordId, setSelectedRecordId] = useState(null);
  const [criticInputs, setCriticInputs] = useState({ common: '0.200' });
  const [latestCalibration, setLatestCalibration] = useState(null);
  const [calibrationProgress, setCalibrationProgress] = useState(null);
  const [showCalibrationManager, setShowCalibrationManager] = useState(false);

  // ─── Refs ────────────────────────────────────────────────
  const appModeRef = useRef(appMode);
  const showCalibrationManagerRef = useRef(showCalibrationManager);
  const selectedRecordIdRef = useRef(selectedRecordId);
  const countdownIntervalId = useRef(null);
  const latestCalibrationRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const ws = useRef(null);
  const frameSenderIntervalId = useRef(null);
  const selectedExerciseRef = useRef(null);
  const awaitingResponseRef = useRef(false);

  // ─── Callbacks ───────────────────────────────────────────
  const sendCommand = useCallback((payload) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) return;
    const message = { ...payload };
    if (!message.exercise) message.exercise = selectedExerciseRef.current;
    ws.current.send(JSON.stringify(message));
  }, []);

  const updateSummary = useCallback((exercise, updater) => {
    setCalibrationSummary(prev => {
      const prevInfo = prev[exercise] ? { ...prev[exercise] } : createDefaultSummary();
      return { ...prev, [exercise]: updater(prevInfo) };
    });
  }, []);

  const resetMetrics = useCallback(() => {
    setWorkoutSummary(null); setRepCounter(0); setErrorReps(0);
    setRepTimestamps([]); setFeedbackMessage(''); setLlmFeedback('');
    setFeedbackLandmarks([]); setArrowFeedback([]); setPoseLandmarks([]);
    setLeftElbowAngle(null); setRightElbowAngle(null);
    setLeftKneeAngle(null); setRightKneeAngle(null);
    setLatencyMs(null); setRoundTripMs(null); setCalibrationProgress(null);
    setCountdown(null); awaitingResponseRef.current = false;
    setBackendName(null); setSessionProgress(null);
    setFormAnalysis(null); setFormSnapshots([]); setPostRepCommand(null);
  }, []);

  // ─── Sync refs ───────────────────────────────────────────
  useEffect(() => { appModeRef.current = appMode; }, [appMode]);
  useEffect(() => { showCalibrationManagerRef.current = showCalibrationManager; }, [showCalibrationManager]);
  useEffect(() => { selectedRecordIdRef.current = selectedRecordId; }, [selectedRecordId]);
  useEffect(() => { latestCalibrationRef.current = latestCalibration; }, [latestCalibration]);
  useEffect(() => { repCounterRef.current = repCounter; }, [repCounter]);

  // ─── Calibration sync ───────────────────────────────────
  useEffect(() => {
    const summary = selectedExercise ? (calibrationSummary[selectedExercise] || createDefaultSummary()) : createDefaultSummary();
    const critics = summary.critics || { common: 0.2 };
    setCriticInputs({ common: Number(critics.common ?? 0.2).toFixed(3) });
  }, [selectedExercise, calibrationSummary]);

  useEffect(() => {
    if (!selectedExercise) return;
    const summary = calibrationSummary[selectedExercise];
    if (!summary) return;
    if (showCalibrationManager) {
      if (selectedRecordId && !summary.records.some(r => r.id === selectedRecordId)) {
        const fallback = summary.records[0] ? summary.records[0].id : null;
        selectedRecordIdRef.current = fallback;
        setSelectedRecordId(fallback);
      } else if (!selectedRecordId && summary.records.length) {
        selectedRecordIdRef.current = summary.records[0].id;
        setSelectedRecordId(summary.records[0].id);
      }
    } else if (selectedRecordId !== null) {
      selectedRecordIdRef.current = null;
      setSelectedRecordId(null);
    }
  }, [selectedExercise, calibrationSummary, selectedRecordId, showCalibrationManager]);

  // ─── MediaPipe check ─────────────────────────────────────
  useEffect(() => {
    const id = setInterval(() => {
      if (window.drawConnectors && window.POSE_CONNECTIONS) {
        setIsMediaPipeReady(true);
        clearInterval(id);
      }
    }, 100);
    return () => clearInterval(id);
  }, []);

  // ─── WebSocket ───────────────────────────────────────────
  useEffect(() => {
    if (!isMediaPipeReady) return undefined;
    let cancelled = false;
    let reconnectTimer = null;

    const ensureConnection = () => {
      if (cancelled) return;
      if (ws.current && ws.current.readyState !== WebSocket.CLOSED) return;
      setStatus('Connecting…'); setConnectionState('connecting');
      const socket = new WebSocket(`${WS_URL}/ws`);
      ws.current = socket;

      socket.onopen = () => {
        if (cancelled) return;
        setStatus('Connected'); setConnectionState('connected');
        awaitingResponseRef.current = false;
        if (selectedExerciseRef.current) {
          socket.send(JSON.stringify({ command: 'select_exercise', exercise: selectedExerciseRef.current }));
          socket.send(JSON.stringify({ command: 'list_calibrations', exercise: selectedExerciseRef.current }));
          socket.send(JSON.stringify({ command: 'set_mode', mode: appModeRef.current, exercise: selectedExerciseRef.current }));
        }
      };

      socket.onclose = () => {
        awaitingResponseRef.current = false;
        if (cancelled) return;
        setStatus('Disconnected'); setConnectionState('disconnected');
        ws.current = null;
        reconnectTimer = setTimeout(ensureConnection, 1500);
      };

      socket.onerror = () => {
        if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) socket.close();
      };

      socket.onmessage = (event) => {
        awaitingResponseRef.current = false;
        const showManager = showCalibrationManagerRef.current;
        const currentSelectedId = selectedRecordIdRef.current;
        const data = JSON.parse(event.data);

        if (data.event) {
          handleEvent(data, showManager, currentSelectedId);
          return;
        }

        if (data.summary) {
          setWorkoutSummary({ total_reps: 0, success_rate: 0, mistakes: {}, avg_tempo: 0, exercise: selectedExerciseRef.current || '', ...data.summary });
          return;
        }

        handleLandmarkData(data);
      };
    };

    ensureConnection();
    return () => { cancelled = true; if (reconnectTimer) clearTimeout(reconnectTimer); if (ws.current) { ws.current.close(); ws.current = null; } };
  }, [isMediaPipeReady, updateSummary, sendCommand]);

  // ─── Event handler (extracted for clarity) ───────────────
  const handleEvent = useCallback((data, showManager, currentSelectedId) => {
    const et = data.event;
    if (et === 'exercise_selected') {
      updateSummary(data.exercise, () => ({ records: data.records || [], active: data.active || { common: null, calibration: null }, critics: data.critics || { common: 0.2, calibration: 0.2 } }));
      if (data.mode) setAppMode(data.mode);
      return;
    }
    if (et === 'mode_updated') {
      setAppMode(data.mode);
      if (data.activeCalibration) { selectedRecordIdRef.current = data.activeCalibration.id || null; setSelectedRecordId(data.activeCalibration.id || null); }
      if (data.critics) updateSummary(data.exercise, prev => ({ ...prev, critics: data.critics, active: prev.active || { common: null, calibration: null } }));
      return;
    }
    if (et === 'critic_updated') { updateSummary(data.exercise, prev => ({ ...prev, critics: data.critics || prev.critics })); return; }
    if (et === 'calibration_list') {
      updateSummary(data.exercise, () => ({ records: data.records || [], active: data.active || { common: null, calibration: null }, critics: data.critics || { common: 0.2, calibration: 0.2 } }));
      return;
    }
    if (et === 'calibration_applied') {
      updateSummary(data.exercise, prev => ({ ...prev, active: { ...prev.active, [data.mode]: data.activeCalibration ? data.activeCalibration.id : null } }));
      if (data.activeCalibration) { selectedRecordIdRef.current = data.activeCalibration.id; setSelectedRecordId(data.activeCalibration.id); }
      return;
    }
    if (et === 'calibration_deleted') {
      updateSummary(data.exercise, () => ({ records: data.records || [], active: data.active || { common: null, calibration: null }, critics: data.critics || { common: 0.2, calibration: 0.2 } }));
      setStatus('Calibration deleted.');
      return;
    }
    if (et === 'calibration_started') { setStatus('Calibrating — perform full reps.'); setCalibrationProgress(null); setAppState('calibrating_live'); return; }
    if (et === 'calibration_complete') {
      const record = data.record;
      setCalibrationProgress(null);
      if (record) {
        updateSummary(data.exercise, prev => ({ ...prev, records: [record, ...prev.records.filter(r => r.id !== record.id)], active: { ...prev.active, [data.mode]: record.id } }));
        latestCalibrationRef.current = { exercise: data.exercise, record };
        setLatestCalibration({ exercise: data.exercise, record });
        selectedRecordIdRef.current = record.id; setSelectedRecordId(record.id);
        setAppMode('common'); setAppState('selection');
        setStatus('Calibration saved!');
        sendCommand({ command: 'set_mode', mode: 'common', exercise: data.exercise });
        sendCommand({ command: 'list_calibrations', exercise: data.exercise });
      }
      return;
    }
    if (et === 'calibration_error') { setCalibrationProgress(null); if (data.message) setStatus(`Error: ${data.message}`); setAppState('selection'); return; }
    if (et === 'calibration_cancelled') { setCalibrationProgress(null); setAppState('selection'); setStatus('Calibration cancelled.'); return; }
    if (et === 'session_started') {
      setSessionProgress(data.progress);
      if (data.progress?.current_exercise) { setSelectedExercise(data.progress.current_exercise); selectedExerciseRef.current = data.progress.current_exercise; }
      setAppState('workout'); setStatus(`Session: ${data.progress?.session_name || 'Workout'}`); return;
    }
    if (et === 'set_started' || et === 'set_skipped') {
      setSessionProgress(data.progress);
      if (data.progress?.current_exercise) { setSelectedExercise(data.progress.current_exercise); selectedExerciseRef.current = data.progress.current_exercise; }
      setRepCounter(0); return;
    }
    if (et === 'session_complete') { setSessionProgress(data.progress); if (data.session) { saveSessionData(data.session); sendSessionToLLM(data.session); } return; }
    if (et === 'session_ended') { if (data.session) { saveSessionData(data.session); sendSessionToLLM(data.session); } setSessionProgress(null); return; }
    if (et === 'session_error') { setStatus(`Error: ${data.message}`); return; }
    if (et === 'session_progress') { if (data.progress) setSessionProgress(data.progress); return; }
  }, [updateSummary, sendCommand]);

  // ─── Landmark data handler ───────────────────────────────
  const handleLandmarkData = useCallback((data) => {
    if (data.backend) setBackendName(data.backend);
    if (!data.landmarks) return;
    if (data.hasOwnProperty('rep_count')) setRepCounter(data.rep_count);
    if (data.hasOwnProperty('latency_ms')) setLatencyMs(data.latency_ms);
    if (data.hasOwnProperty('client_ts')) { const rtt = performance.now() - data.client_ts; if (Number.isFinite(rtt)) setRoundTripMs(rtt); }
    if (data.left_knee_angle) setLeftKneeAngle(data.left_knee_angle.toFixed(2));
    if (data.right_knee_angle) setRightKneeAngle(data.right_knee_angle.toFixed(2));
    if (data.left_elbow_angle) setLeftElbowAngle(data.left_elbow_angle.toFixed(2));
    if (data.right_elbow_angle) setRightElbowAngle(data.right_elbow_angle.toFixed(2));
    if (data.feedback) {
      const isPositive = ['good rep', 'great curl', 'good depth', 'perfect'].some(p => data.feedback.toLowerCase().includes(p));
      setFeedbackMessage(isPositive ? '' : data.feedback);
      const isError = !isPositive && data.feedback.trim() !== '';
      if (isError && repCounterRef.current > 0 && lastErrorRep.current !== repCounterRef.current) { setErrorReps(prev => prev + 1); lastErrorRep.current = repCounterRef.current; }
    } else { setFeedbackMessage(''); }
    if (data.arrow_feedback) setArrowFeedback(data.arrow_feedback); else setArrowFeedback([]);
    if (data.coach_tip) setLlmFeedback(data.coach_tip);
    if (data.post_rep_command !== undefined) setPostRepCommand(data.post_rep_command);
    if (data.feedback_landmarks) setFeedbackLandmarks(data.feedback_landmarks);
    if (data.calibration_progress) setCalibrationProgress(data.calibration_progress);
    if (data.rep_timestamps) setRepTimestamps(data.rep_timestamps);
    if (data.session_progress) setSessionProgress(data.session_progress);
    if (data.form_snapshots && data.form_snapshots.length > 0) setFormSnapshots(data.form_snapshots);
    else if (data.session_progress?.current_set?.form_snapshots) setFormSnapshots(data.session_progress.current_set.form_snapshots);
    setPoseLandmarks(data.landmarks);
  }, []);

  // ─── Camera lifecycle ────────────────────────────────────
  useEffect(() => {
    if (!isMediaPipeReady) return;
    const streamingStates = ['calibration_countdown', 'calibrating_live', 'workout'];
    const shouldStream = streamingStates.includes(appState);
    if (!shouldStream) {
      clearInterval(frameSenderIntervalId.current);
      awaitingResponseRef.current = false;
      if (videoRef.current?.srcObject) { videoRef.current.srcObject.getTracks().forEach(t => t.stop()); videoRef.current.srcObject = null; }
      return;
    }
    if (!videoRef.current?.srcObject) {
      (async () => {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ video: true });
          if (videoRef.current) videoRef.current.srcObject = stream;
        } catch (err) { setStatus('Camera error'); }
      })();
    }
  }, [appState, isMediaPipeReady]);

  useEffect(() => {
    return () => {
      clearInterval(frameSenderIntervalId.current);
      if (countdownIntervalId.current) { clearInterval(countdownIntervalId.current); countdownIntervalId.current = null; }
      if (videoRef.current?.srcObject) { videoRef.current.srcObject.getTracks().forEach(t => t.stop()); videoRef.current.srcObject = null; }
    };
  }, []);

  useEffect(() => {
    selectedExerciseRef.current = selectedExercise;
    if (appState === 'workout' && selectedExercise && ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ command: 'select_exercise', exercise: selectedExercise }));
    }
  }, [selectedExercise, appState]);

  // ─── Frame sender ───────────────────────────────────────
  const startSendingFrames = () => {
    awaitingResponseRef.current = false;
    frameSenderIntervalId.current = setInterval(() => {
      if (awaitingResponseRef.current) return;
      if (ws.current?.readyState === WebSocket.OPEN && videoRef.current && canvasRef.current) {
        const video = videoRef.current;
        if (video.videoWidth === 0) return;
        const canvas = canvasRef.current;
        const context = canvas.getContext('2d');
        canvas.width = video.videoWidth; canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        const frame = canvas.toDataURL('image/jpeg', 0.8);
        if (frame.length > 100) {
          try { ws.current.send(JSON.stringify({ frame, ts: performance.now() })); awaitingResponseRef.current = true; }
          catch { awaitingResponseRef.current = false; }
        }
      }
    }, 1000 / 30);
  };

  // ─── Actions ─────────────────────────────────────────────
  const handleSelectExercise = (exercise) => {
    if (selectedExerciseRef.current !== exercise) {
      resetMetrics(); latestCalibrationRef.current = null; setLatestCalibration(null);
      setSelectedRecordId(null); selectedRecordIdRef.current = null;
      showCalibrationManagerRef.current = false; setShowCalibrationManager(false);
    }
    setSelectedExercise(exercise); selectedExerciseRef.current = exercise;
    setStatus(`${EXERCISES.find(e => e.id === exercise)?.label} selected`);
    sendCommand({ command: 'select_exercise', exercise });
    sendCommand({ command: 'list_calibrations', exercise });
  };

  const beginWorkout = () => {
    if (!selectedExerciseRef.current) return;
    resetMetrics();
    setAppMode('common'); showCalibrationManagerRef.current = false; setShowCalibrationManager(false);
    sendCommand({ command: 'set_mode', mode: 'common', exercise: selectedExerciseRef.current });
    setAppState('workout'); setStatus('Workout started');
  };

  const openSessionBuilder = () => {
    setSessionConfig([]); setSessionName('My Workout');
    setAppState('session_builder');
  };

  const startSession = () => {
    if (sessionConfig.length === 0) return;
    resetMetrics();
    setAppMode('common'); showCalibrationManagerRef.current = false; setShowCalibrationManager(false);
    sendCommand({ command: 'start_session', name: sessionName, sets: sessionConfig });
  };

  const beginCalibration = () => {
    if (!selectedExerciseRef.current) return;
    resetMetrics();
    setAppMode('calibration'); showCalibrationManagerRef.current = false; setShowCalibrationManager(false);
    sendCommand({ command: 'set_mode', mode: 'calibration', exercise: selectedExerciseRef.current });
    setCalibrationProgress(null);
    if (countdownIntervalId.current) { clearInterval(countdownIntervalId.current); countdownIntervalId.current = null; }
    let remaining = 5; setCountdown(remaining); setAppState('calibration_countdown');
    setStatus('Get into starting position…');
    countdownIntervalId.current = setInterval(() => {
      remaining -= 1; setCountdown(remaining);
      if (remaining <= 0) {
        clearInterval(countdownIntervalId.current); countdownIntervalId.current = null; setCountdown(null);
        sendCommand({ command: 'start_auto_calibration', exercise: selectedExerciseRef.current });
        setAppState('calibrating_live');
      }
    }, 1000);
  };

  const finishCalibration = () => {
    if (!selectedExerciseRef.current) return;
    setAppState('calibration_saving');
    sendCommand({ command: 'finalize_auto_calibration', exercise: selectedExerciseRef.current });
  };

  const cancelCalibration = useCallback(() => {
    if (countdownIntervalId.current) { clearInterval(countdownIntervalId.current); countdownIntervalId.current = null; }
    setCountdown(null);
    if (!selectedExerciseRef.current) { setAppState('selection'); return; }
    setAppMode('common'); appModeRef.current = 'common';
    showCalibrationManagerRef.current = false; setShowCalibrationManager(false);
    setAppState('selection'); setStatus('Calibration cancelled.');
    sendCommand({ command: 'set_mode', mode: 'common', exercise: selectedExerciseRef.current });
    sendCommand({ command: 'cancel_calibration', exercise: selectedExerciseRef.current });
  }, [sendCommand]);

  const resetApp = () => {
    setAppState('selection'); resetMetrics();
    setSelectedExercise(null); selectedExerciseRef.current = null;
    setAppMode('common'); selectedRecordIdRef.current = null; setSelectedRecordId(null);
    latestCalibrationRef.current = null; setLatestCalibration(null);
    showCalibrationManagerRef.current = false; setShowCalibrationManager(false);
  };

  // ─── Workout end / summary ──────────────────────────────
  const calculateRepDurations = (timestamps) => { if (timestamps.length < 2) return []; const d = []; for (let i = 1; i < timestamps.length; i++) d.push(timestamps[i] - timestamps[i - 1]); return d; };
  const calculateAverageTempo = (durations) => durations.length === 0 ? 0 : durations.reduce((a, b) => a + b, 0) / durations.length;

  const endWorkout = () => {
    if (ws.current?.readyState === WebSocket.OPEN) ws.current.send(JSON.stringify({ command: 'reset' }));
    const durations = calculateRepDurations(repTimestamps);
    const successRate = repCounter > 0 ? (repCounter - errorReps) / repCounter : 0;
    const summary = { total_reps: repCounter, success_rate: successRate, mistakes: { errors_detected: errorReps }, avg_tempo: calculateAverageTempo(durations), rep_durations: durations, exercise: selectedExerciseRef.current };
    setWorkoutSummary(summary); workoutSummaryRef.current = summary; setAppState('summary');
    saveWorkoutData(summary);
    if (formSnapshots.length > 0) fetchFormAnalysisAndSummary(selectedExerciseRef.current, formSnapshots, repCounter, summary);
    else fetchLlmSummary(summary);
  };

  const endSession = () => { sendCommand({ command: 'end_session' }); };

  const sendSessionToLLM = (sessionData) => {
    const rawSuccessRate = sessionData.total_reps_target > 0 ? sessionData.total_reps_completed / sessionData.total_reps_target : 0;
    const avgTempo = sessionData.duration_seconds > 0 && sessionData.total_reps_completed > 0 ? sessionData.duration_seconds / sessionData.total_reps_completed : 0;
    const mistakesObj = sessionData.all_mistakes || {};
    const totalErrors = Object.values(mistakesObj).reduce((sum, c) => sum + c, 0);
    const sessionSummary = { total_reps: sessionData.total_reps_completed, success_rate: Math.min(1, rawSuccessRate), mistakes: { errors_detected: totalErrors, ...mistakesObj }, avg_tempo: avgTempo, exercise: `session: ${sessionData.name}`, session_details: sessionData };
    setWorkoutSummary(sessionSummary); workoutSummaryRef.current = sessionSummary; setAppState('summary');
    const allSnaps = []; if (sessionData.sets) sessionData.sets.forEach(s => { if (s.form_snapshots?.length) allSnaps.push(...s.form_snapshots); });
    const primaryEx = sessionData.sets?.[0]?.exercise || 'workout';
    if (allSnaps.length > 0) fetchFormAnalysisAndSummary(primaryEx, allSnaps, sessionData.total_reps_completed, sessionSummary);
    else fetchLlmSummary(sessionSummary);
  };

  const saveSessionData = async (d) => { try { await fetch(`${BACKEND_URL}/save_session`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(d) }); } catch {} };
  const saveWorkoutData = async (d) => { if (!d.exercise) return; try { await fetch(`${BACKEND_URL}/save_workout`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(d) }); } catch {} };

  const fetchFormAnalysisAndSummary = async (exercise, snapshots, totalReps, sessionData) => {
    if (!exercise || !snapshots.length) return;
    try {
      const res = await fetch(`${BACKEND_URL}/analyze_form`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ exercise, form_snapshots: snapshots, total_reps: totalReps }) });
      const d = await res.json();
      if (d.status === 'success') {
        setFormAnalysis(d.analysis);
        fetchLlmSummary({ ...sessionData, form_analysis: { score: d.analysis.score, good_reps: d.analysis.good_reps, total_reps: d.analysis.total_reps, top_issues: d.analysis.top_issues, form_states_count: d.analysis.form_states_count, snapshots: d.analysis.snapshots } });
      } else fetchLlmSummary(sessionData);
    } catch { fetchLlmSummary(sessionData); }
  };

  const fetchLlmSummary = async (sessionData) => {
    if (!sessionData.exercise) return;
    setIsLlmLoading(true);
    try { const r = await fetch(`${BACKEND_URL}/summary`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(sessionData) }); const d = await r.json(); setLlmSummary(d.summary); setChatHistory([]); }
    catch { setLlmSummary('Could not load AI summary.'); }
    finally { setIsLlmLoading(false); }
  };

  const handleAskQuestion = async (question) => {
    if (!question.trim() || !workoutSummaryRef.current) return;
    const newHistory = [...chatHistory, { role: 'user', content: question }]; setChatHistory(newHistory); setIsLlmLoading(true);
    try { const r = await fetch(`${BACKEND_URL}/ask`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_data: workoutSummaryRef.current, question }) }); const d = await r.json(); setChatHistory([...newHistory, { role: 'assistant', content: d.answer }]); }
    catch { setChatHistory([...newHistory, { role: 'assistant', content: 'Sorry, something went wrong.' }]); }
    finally { setIsLlmLoading(false); }
  };

  // ─── Derived ─────────────────────────────────────────────
  const currentSummary = selectedExercise ? (calibrationSummary[selectedExercise] || createDefaultSummary()) : createDefaultSummary();
  const currentRecords = currentSummary.records || [];

  // Camera JSX is inlined directly to prevent React from remounting the video element

  // ═══════════════════════════════════════════════════════════
  //  R E N D E R
  // ═══════════════════════════════════════════════════════════
  return (
    <div className="app-shell">
      {/* ─── Top Bar ─── */}
      <header className="top-bar">
        <div className="top-bar-brand">
          <div className="logo-icon">F</div>
          <h1>FitCoachAR</h1>
        </div>
        <div className="top-bar-status">
          <span className={`status-dot ${connectionState}`} />
          <span>{status}</span>
        </div>
        <div className="top-bar-meta">
          {backendName && <span className="meta-chip">{backendName}</span>}
          {latencyMs !== null && <span className="meta-chip">{latencyMs.toFixed(0)}ms</span>}
        </div>
      </header>

      <main className="main-content">
        {/* ─── Loading ─── */}
        {!isMediaPipeReady && <div className="landing-page"><p style={{ color: 'var(--text-muted)' }}>Loading pose estimation libraries…</p></div>}

        {/* ═══ SELECTION ═══ */}
        {isMediaPipeReady && appState === 'selection' && (
          <div className="landing-page">
            <div className="landing-hero">
              <h2>Your AI Fitness Coach</h2>
              <p>Select an exercise to begin. FitCoachAR uses real-time pose estimation and AR feedback to guide your workout form.</p>
            </div>
            <div className="exercise-cards">
              {EXERCISES.map(ex => (
                <div key={ex.id} className={`exercise-card ${selectedExercise === ex.id ? 'selected' : ''}`} onClick={() => handleSelectExercise(ex.id)} id={`exercise-card-${ex.id}`}>
                  <div className="card-icon">{ex.icon}</div>
                  <h3>{ex.label}</h3>
                  <p>{ex.description}</p>
                </div>
              ))}
            </div>
            <div className="landing-actions">
              <button className="btn btn-primary btn-lg" disabled={!selectedExercise} onClick={beginWorkout} id="btn-quick-workout">
                <span className="btn-icon">▶</span> Quick Workout
              </button>
              <button className="btn btn-secondary btn-lg" onClick={openSessionBuilder} id="btn-build-session">
                <span className="btn-icon">📋</span> Build Session
              </button>
              <button className="btn btn-secondary btn-lg" disabled={!selectedExercise} onClick={beginCalibration} id="btn-calibrate">
                <span className="btn-icon">🎯</span> Calibrate
              </button>
            </div>

            {/* Calibration Manager Inline */}
            {selectedExercise && showCalibrationManager && currentRecords.length > 0 && (
              <div className="calibration-manager" style={{ width: '100%', maxWidth: '600px' }}>
                <div className="sidebar-card">
                  <h3>Saved Calibrations</h3>
                  <div className="calibration-records-grid">
                    {currentRecords.map(record => {
                      const isActive = currentSummary.active?.common === record.id;
                      return (
                        <div key={record.id} className={`cal-record ${isActive ? 'active' : ''}`}>
                          <div className="cal-meta">
                            <div className="cal-date">{new Date(record.timestamp).toLocaleString()}</div>
                            <div className="cal-eta">{record.eta ? Object.entries(record.eta).map(([k, v]) => `${k}: ${(v * 100).toFixed(1)}%`).join(' · ') : ''}</div>
                          </div>
                          {isActive && <span className="cal-badge">Active</span>}
                          <div className="cal-actions">
                            <button className="btn btn-secondary" onClick={() => sendCommand({ command: 'use_calibration', record_id: record.id, mode: 'common' })}>Use</button>
                            <button className="btn btn-danger" onClick={() => sendCommand({ command: 'delete_calibration', exercise: selectedExerciseRef.current, record_id: record.id })}>✕</button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
            {selectedExercise && (
              <button className="btn btn-secondary" onClick={() => { const next = !showCalibrationManager; showCalibrationManagerRef.current = next; setShowCalibrationManager(next); if (next) sendCommand({ command: 'list_calibrations', exercise: selectedExerciseRef.current }); }} style={{ marginTop: '-12px' }}>
                {showCalibrationManager ? 'Hide Calibrations' : 'Manage Calibrations'}
              </button>
            )}
          </div>
        )}

        {/* ═══ SESSION BUILDER ═══ */}
        {isMediaPipeReady && appState === 'session_builder' && (
          <SessionBuilderView
            sessionConfig={sessionConfig} setSessionConfig={setSessionConfig}
            sessionName={sessionName} setSessionName={setSessionName}
            exercises={EXERCISES} presets={SESSION_PRESETS}
            onStart={startSession} onCancel={() => setAppState('selection')}
          />
        )}

        {/* ═══ CALIBRATION COUNTDOWN ═══ */}
        {isMediaPipeReady && appState === 'calibration_countdown' && (
          <div className="calibration-view">
            <div className="calibration-header">
              <h2>Calibrating {selectedExercise === 'bicep_curls' ? 'Bicep Curls' : 'Squats'}</h2>
              <p>Get into your starting position</p>
            </div>
            <div className="countdown-display">{countdown ?? 0}</div>
            <div className="calibration-camera">
              <div className="camera-container">
                <video ref={videoRef} onCanPlay={startSendingFrames} autoPlay playsInline muted />
                <canvas ref={canvasRef} className="frame-canvas" />
                <AROverlay landmarks={poseLandmarks} feedbackLandmarks={feedbackLandmarks} arrowFeedback={arrowFeedback} selectedExercise={selectedExercise} backend={backendName}
                  currentAngles={{ rightElbow: rightElbowAngle ? parseFloat(rightElbowAngle) : 0, rightKnee: rightKneeAngle ? parseFloat(rightKneeAngle) : 0 }}
                  targetAngles={{ rightElbow: 45, rightKnee: 90 }} />
                {feedbackMessage && <div className="camera-feedback-overlay"><span className="feedback-text">{feedbackMessage}</span></div>}
              </div>
            </div>
            <div className="calibration-actions">
              <button className="btn btn-danger" onClick={cancelCalibration}>Cancel</button>
            </div>
          </div>
        )}

        {/* ═══ CALIBRATING LIVE ═══ */}
        {isMediaPipeReady && appState === 'calibrating_live' && (
          <div className="calibration-view">
            <div className="calibration-header">
              <h2>Calibrating…</h2>
              <p>Perform a few full reps. We'll detect your range automatically.</p>
            </div>
            {calibrationProgress && (
              <div className="sidebar-card calibration-progress-card">
                <h3>Detected Range</h3>
                <div className="range-item"><span className="range-label">{selectedExercise === 'bicep_curls' ? 'Extended (max)' : 'Standing (max)'}</span><span className="range-value">{calibrationProgress.max_angle ? `${calibrationProgress.max_angle.toFixed(1)}°` : '—'}</span></div>
                <div className="range-item"><span className="range-label">{selectedExercise === 'bicep_curls' ? 'Contracted (min)' : 'Deepest (min)'}</span><span className="range-value">{calibrationProgress.min_angle ? `${calibrationProgress.min_angle.toFixed(1)}°` : '—'}</span></div>
                {calibrationProgress.frozen && <div className="frozen-notice">✓ Range locked — you can click Finish now</div>}
              </div>
            )}
            <div className="calibration-camera">
              <div className="camera-container">
                <video ref={videoRef} onCanPlay={startSendingFrames} autoPlay playsInline muted />
                <canvas ref={canvasRef} className="frame-canvas" />
                <AROverlay landmarks={poseLandmarks} feedbackLandmarks={feedbackLandmarks} arrowFeedback={arrowFeedback} selectedExercise={selectedExercise} backend={backendName}
                  currentAngles={{ rightElbow: rightElbowAngle ? parseFloat(rightElbowAngle) : 0, rightKnee: rightKneeAngle ? parseFloat(rightKneeAngle) : 0 }}
                  targetAngles={{ rightElbow: 45, rightKnee: 90 }} />
                {feedbackMessage && <div className="camera-feedback-overlay"><span className="feedback-text">{feedbackMessage}</span></div>}
              </div>
            </div>
            <div className="calibration-actions">
              <button className="btn btn-success btn-lg" onClick={finishCalibration} disabled={!calibrationProgress || calibrationProgress.min_angle === null || calibrationProgress.max_angle === null}>
                ✓ Finish Calibration
              </button>
              <button className="btn btn-danger" onClick={cancelCalibration}>Cancel</button>
            </div>
          </div>
        )}

        {/* ═══ CALIBRATION SAVING ═══ */}
        {isMediaPipeReady && appState === 'calibration_saving' && (
          <div className="calibration-view">
            <div className="calibration-header">
              <h2>Saving…</h2>
              <p>Processing your calibration data</p>
            </div>
          </div>
        )}

        {/* ═══ WORKOUT ═══ */}
        {isMediaPipeReady && appState === 'workout' && (
          <div className="workout-layout">
            <div className="workout-camera-section">
              <div className="camera-container">
                <video ref={videoRef} onCanPlay={startSendingFrames} autoPlay playsInline muted />
                <canvas ref={canvasRef} className="frame-canvas" />
                <AROverlay landmarks={poseLandmarks} feedbackLandmarks={feedbackLandmarks} arrowFeedback={arrowFeedback} selectedExercise={selectedExercise} backend={backendName}
                  currentAngles={{ rightElbow: rightElbowAngle ? parseFloat(rightElbowAngle) : 0, rightKnee: rightKneeAngle ? parseFloat(rightKneeAngle) : 0 }}
                  targetAngles={{ rightElbow: 45, rightKnee: 90 }} />
                {feedbackMessage && <div className="camera-feedback-overlay"><span className="feedback-text">{feedbackMessage}</span></div>}
              </div>
            </div>
            <div className="workout-sidebar">
              {/* End button */}
              <button className="btn btn-danger" onClick={sessionProgress ? endSession : endWorkout} style={{ width: '100%' }} id="btn-end-workout">
                {sessionProgress ? 'End Session' : 'End Workout'}
              </button>

              {/* Session progress */}
              {sessionProgress && (
                <div className="sidebar-card session-bar">
                  <div className="session-bar-header">
                    <span className="session-title">{sessionProgress.session_name}</span>
                    <span className="set-info">Set {sessionProgress.current_set_index + 1}/{sessionProgress.total_sets}</span>
                  </div>
                  {sessionProgress.current_set && (
                    <>
                      <div className="progress-track">
                        <div className="progress-fill" style={{ width: `${Math.min(100, (sessionProgress.current_set.completed_reps / sessionProgress.current_set.target_reps) * 100)}%` }} />
                      </div>
                      <div className="progress-label">{sessionProgress.current_set.completed_reps} / {sessionProgress.current_set.target_reps} reps</div>
                    </>
                  )}
                  <div className="session-actions">
                    {sessionProgress.current_set?.is_complete && !sessionProgress.is_complete && (
                      <button className="btn btn-primary" onClick={() => sendCommand({ command: 'next_set' })}>Next Set →</button>
                    )}
                    {!sessionProgress.current_set?.is_complete && (
                      <button className="btn btn-secondary" onClick={() => sendCommand({ command: 'skip_set' })}>Skip</button>
                    )}
                  </div>
                  {sessionProgress.is_complete && <div className="session-complete-badge">🎉 Session Complete!</div>}
                </div>
              )}

              {/* Rep counter */}
              <div className="sidebar-card">
                <h3>Reps</h3>
                <div className="rep-display">
                  <div className="rep-number">{repCounter}</div>
                  <div className="rep-label">{EXERCISES.find(e => e.id === selectedExercise)?.label || 'Exercise'}</div>
                </div>
              </div>

              {/* Post-rep coaching */}
              {postRepCommand && <div className="coaching-command">{postRepCommand}</div>}

              {/* Angles */}
              <div className="sidebar-card">
                <h3>Joint Angles</h3>
                <div className="angle-grid">
                  {selectedExercise === 'bicep_curls' && <>
                    <div className="angle-item"><div className="angle-label">Left Elbow</div><div className="angle-value">{leftElbowAngle ? `${leftElbowAngle}°` : '—'}</div></div>
                    <div className="angle-item"><div className="angle-label">Right Elbow</div><div className="angle-value">{rightElbowAngle ? `${rightElbowAngle}°` : '—'}</div></div>
                  </>}
                  {selectedExercise === 'squats' && <>
                    <div className="angle-item"><div className="angle-label">Left Knee</div><div className="angle-value">{leftKneeAngle ? `${leftKneeAngle}°` : '—'}</div></div>
                    <div className="angle-item"><div className="angle-label">Right Knee</div><div className="angle-value">{rightKneeAngle ? `${rightKneeAngle}°` : '—'}</div></div>
                  </>}
                </div>
              </div>

              {/* Latency */}
              {(latencyMs !== null || roundTripMs !== null) && (
                <div className="sidebar-card">
                  <h3>Performance</h3>
                  <div className="latency-row">
                    {latencyMs !== null && <div className="latency-badge"><span className="latency-value">{latencyMs.toFixed(0)}</span>ms backend</div>}
                    {roundTripMs !== null && <div className="latency-badge"><span className="latency-value">{roundTripMs.toFixed(0)}</span>ms total</div>}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ═══ SUMMARY ═══ */}
        {isMediaPipeReady && appState === 'summary' && (
          <SummaryView
            formAnalysis={formAnalysis} llmSummary={llmSummary} isLlmLoading={isLlmLoading}
            chatHistory={chatHistory} onAskQuestion={handleAskQuestion} onReset={resetApp}
          />
        )}
      </main>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
//  S U B - C O M P O N E N T S
// ═══════════════════════════════════════════════════════════

function SummaryView({ formAnalysis, llmSummary, isLlmLoading, chatHistory, onAskQuestion, onReset }) {
  const [question, setQuestion] = useState('');
  const chatRef = useRef(null);
  useEffect(() => { if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight; }, [chatHistory]);
  const handleSubmit = (e) => { e.preventDefault(); onAskQuestion(question); setQuestion(''); };

  const scoreColor = formAnalysis ? (formAnalysis.score >= 70 ? 'var(--green)' : formAnalysis.score >= 40 ? 'var(--yellow)' : 'var(--red)') : 'var(--accent)';
  const circumference = 2 * Math.PI * 48;
  const offset = formAnalysis ? circumference - (formAnalysis.score / 100) * circumference : circumference;

  return (
    <div className="summary-view">
      <h2>Workout Complete 🎉</h2>

      {formAnalysis && (
        <div className="sidebar-card">
          <h3>Form Analysis</h3>
          <div className="form-score-section">
            <div className="score-ring">
              <svg viewBox="0 0 120 120">
                <circle className="ring-bg" cx="60" cy="60" r="48" />
                <circle className="ring-fill" cx="60" cy="60" r="48" stroke={scoreColor} strokeDasharray={circumference} strokeDashoffset={offset} />
              </svg>
              <div className="score-text">
                <span className="score-number" style={{ color: scoreColor }}>{formAnalysis.score}</span>
                <span className="score-unit">%</span>
              </div>
            </div>
            <div className="score-details">
              <p><strong>{formAnalysis.good_reps}</strong> / {formAnalysis.total_reps} good reps</p>
            </div>
          </div>

          {formAnalysis.top_issues?.length > 0 && (
            <div style={{ marginTop: '16px' }}>
              <h3>Areas to Improve</h3>
              <div className="issues-list">
                {formAnalysis.top_issues.map((issue, i) => (
                  <div key={i} className="issue-item">
                    <div>
                      <div className="issue-name">{(issue.super_form_code || issue.state || 'unknown').replace(/_/g, ' ')}</div>
                      <div className="issue-desc">{issue.description}</div>
                    </div>
                    <span className="issue-count">{issue.count} reps</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {formAnalysis.snapshots?.length > 0 && (
            <div style={{ marginTop: '16px' }}>
              <h3>Rep Breakdown</h3>
              <div className="rep-breakdown-list">
                {formAnalysis.snapshots.map((snap, i) => {
                  const fb = snap.feedback || {};
                  return (
                    <div key={i} className={`rep-row ${fb.is_good ? 'good' : 'bad'}`}>
                      <span className="rep-num">Rep {i + 1}</span>
                      <span className="rep-status-icon">{fb.is_good ? '✓' : '⚠'}</span>
                      <span className="rep-info">{fb.summary || (fb.is_good ? 'Good form' : 'Needs work')}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="sidebar-card ai-summary-card">
        <h3>AI Coach Summary</h3>
        {isLlmLoading && !llmSummary ? <p className="loading-text">Generating your summary…</p> : <p className="summary-text">{llmSummary}</p>}
      </div>

      <div className="sidebar-card chat-section">
        <h3>Ask the Coach</h3>
        <div className="chat-messages" ref={chatRef}>
          {chatHistory.map((msg, i) => (
            <div key={i} className={`chat-msg ${msg.role}`}>
              <strong>{msg.role === 'user' ? 'You' : 'Coach'}:</strong> {msg.content}
            </div>
          ))}
          {isLlmLoading && chatHistory.length > 0 && <div className="chat-msg assistant"><em>Coach is typing…</em></div>}
        </div>
        <form onSubmit={handleSubmit} className="chat-input-row">
          <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask about your form…" disabled={isLlmLoading} id="chat-input" />
          <button type="submit" className="btn btn-primary" disabled={isLlmLoading} id="btn-send-chat">Send</button>
        </form>
      </div>

      <button className="btn btn-primary btn-lg" onClick={onReset} style={{ alignSelf: 'center' }} id="btn-finish-review">Finish Review</button>
    </div>
  );
}

function SessionBuilderView({ sessionConfig, setSessionConfig, sessionName, setSessionName, exercises, presets, onStart, onCancel }) {
  const [selectedExercise, setSelectedExercise] = useState(exercises[0]?.id || 'squats');
  const [reps, setReps] = useState(10);
  const totalReps = sessionConfig.reduce((sum, s) => sum + s.reps, 0);

  return (
    <div className="session-builder-view">
      <h2>Build Your Session</h2>

      <div className="sidebar-card">
        <div className="builder-input-group">
          <label>Session Name</label>
          <input value={sessionName} onChange={(e) => setSessionName(e.target.value)} placeholder="My Workout" id="session-name-input" />
        </div>
      </div>

      <div className="sidebar-card">
        <h3>Quick Presets</h3>
        <div className="preset-grid">
          {presets.map(p => (
            <button key={p.id} className="preset-chip" onClick={() => { setSessionConfig([...p.sets]); setSessionName(p.name); }}>{p.name}</button>
          ))}
        </div>
      </div>

      <div className="sidebar-card">
        <h3>Add a Set</h3>
        <div className="add-set-row">
          <div className="builder-input-group">
            <label>Exercise</label>
            <select value={selectedExercise} onChange={(e) => setSelectedExercise(e.target.value)}>
              {exercises.map(ex => <option key={ex.id} value={ex.id}>{ex.label}</option>)}
            </select>
          </div>
          <div className="builder-input-group">
            <label>Reps</label>
            <input type="number" min="1" max="100" value={reps} onChange={(e) => setReps(parseInt(e.target.value) || 10)} />
          </div>
          <button className="btn btn-primary" onClick={() => setSessionConfig(prev => [...prev, { exercise: selectedExercise, reps: parseInt(reps) || 10 }])}>+ Add</button>
        </div>
      </div>

      <div className="sidebar-card">
        <h3>Your Session ({sessionConfig.length} sets · {totalReps} reps)</h3>
        {sessionConfig.length === 0 ? <p className="empty-message">No sets added yet.</p> : (
          <div className="set-list">
            {sessionConfig.map((s, i) => (
              <div key={i} className="set-item">
                <span className="set-num">#{i + 1}</span>
                <span className="set-name">{exercises.find(e => e.id === s.exercise)?.label || s.exercise}</span>
                <span className="set-reps">{s.reps} reps</span>
                <button className="remove-btn" onClick={() => setSessionConfig(prev => prev.filter((_, j) => j !== i))}>✕</button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="builder-actions">
        <button className="btn btn-primary btn-lg" onClick={onStart} disabled={sessionConfig.length === 0} id="btn-start-session">Start Session</button>
        <button className="btn btn-secondary btn-lg" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

export default App;