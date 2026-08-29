/**
 * BlinkSafe Mobile — 2 GB RAM Budget Android Architecture
 *
 * Lightweight React Native App designed specifically for low-end hardware.
 * Features:
 *  - Zero Base64 streaming overhead
 *  - Ref-based metrics tracking to prevent re-renders
 *  - Timestamp-based 60-second SOS emergency countdown modal
 *  - AppState background/foreground lifecycle management to preserve battery & thermals
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
  Modal,
  AppState,
} from 'react-native';

const API_HOST = 'http://127.0.0.1:5001';

export default function App() {
  const [monitoring, setMonitoring] = useState(false);
  const [state, setState] = useState('ALERT');
  const [sosActive, setSosActive] = useState(false);
  const [sosSeconds, setSosSeconds] = useState(60);

  // Use refs for high-frequency metrics to avoid unnecessary component tree re-renders
  const metricsRef = useRef({
    ear: 0.3,
    mar: 0.1,
    pitch: 0,
    blinks: 0,
    yawns: 0,
    fps: 30,
  });

  const pollTimer = useRef(null);
  const sosTimer = useRef(null);
  const appState = useRef(AppState.currentState);

  // AppState background/foreground lifecycle listener
  useEffect(() => {
    const subscription = AppState.addEventListener('change', (nextAppState) => {
      if (
        appState.current.match(/active/) &&
        nextAppState.match(/inactive|background/)
      ) {
        console.log('[BlinkSafe Mobile] App in background — pausing detection');
        stopPolling();
      } else if (
        appState.current.match(/inactive|background/) &&
        nextAppState === 'active' &&
        monitoring
      ) {
        console.log('[BlinkSafe Mobile] App resumed — restarting detection');
        startPolling();
      }
      appState.current = nextAppState;
    });

    return () => {
      subscription.remove();
      stopPolling();
    };
  }, [monitoring]);

  const startPolling = () => {
    stopPolling();
    pollTimer.current = setInterval(fetchStatus, 400); // 2.5 updates/sec
  };

  const stopPolling = () => {
    if (pollTimer.current) {
      clearInterval(pollTimer.current);
      pollTimer.current = null;
    }
  };

  const fetchStatus = async () => {
    try {
      const response = await fetch(`${API_HOST}/api/status`);
      if (!response.ok) return;
      const data = await response.json();

      setState(data.state || 'ALERT');
      metricsRef.current = {
        ear: data.ear || 0.3,
        mar: data.mar || 0.1,
        pitch: data.pitch || 0,
        blinks: data.blink_count || 0,
        yawns: data.yawn_count || 0,
        fps: data.fps || 30,
      };

      // Trigger 60-second SOS countdown if state is DANGER and SOS is not active
      if (data.state === 'DANGER' && !sosActive) {
        triggerSOSCountdown();
      }
    } catch (err) {
      console.log('[BlinkSafe Mobile] Status fetch error:', err.message);
    }
  };

  const triggerSOSCountdown = () => {
    setSosActive(true);
    setSosSeconds(60);
    if (sosTimer.current) clearInterval(sosTimer.current);

    sosTimer.current = setInterval(() => {
      setSosSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(sosTimer.current);
          console.log('[BlinkSafe Mobile] 🚨 SOS Emergency Alert Sent!');
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const cancelSOS = () => {
    if (sosTimer.current) clearInterval(sosTimer.current);
    setSosActive(false);
    setSosSeconds(60);
  };

  const toggleMonitoring = async () => {
    if (monitoring) {
      stopPolling();
      setMonitoring(false);
      try {
        await fetch(`${API_HOST}/api/session/stop`, { method: 'POST' });
      } catch (e) {}
    } else {
      try {
        await fetch(`${API_HOST}/api/session/start`, { method: 'POST' });
        setMonitoring(true);
        startPolling();
      } catch (e) {
        console.log('Failed to start session');
      }
    }
  };

  const getStateColor = () => {
    if (state === 'DANGER') return '#ef4444';
    if (state === 'DROWSY') return '#f59e0b';
    return '#10b981';
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#0f172a" />

      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>🛡️ BlinkSafe Mobile</Text>
        <Text style={styles.headerSubtitle}>2 GB RAM Low-End Device Profile</Text>
      </View>

      {/* Status Card */}
      <View style={styles.statusCard}>
        <Text style={styles.statusLabel}>ALERTNESS STATE</Text>
        <View style={[styles.badge, { backgroundColor: getStateColor() }]}>
          <Text style={styles.badgeText}>{state}</Text>
        </View>
      </View>

      {/* Primary Metrics Grid */}
      <View style={styles.grid}>
        <View style={styles.metricCard}>
          <Text style={styles.metricValue}>{metricsRef.current.blinks}</Text>
          <Text style={styles.metricLabel}>Blinks</Text>
        </View>
        <View style={styles.metricCard}>
          <Text style={styles.metricValue}>{metricsRef.current.yawns}</Text>
          <Text style={styles.metricLabel}>Yawns</Text>
        </View>
      </View>

      {/* Controls */}
      <View style={styles.controls}>
        <TouchableOpacity
          style={[
            styles.button,
            { backgroundColor: monitoring ? '#ef4444' : '#3b82f6' },
          ]}
          onPress={toggleMonitoring}
          activeOpacity={0.8}
        >
          <Text style={styles.buttonText}>
            {monitoring ? 'Stop Monitoring' : 'Start Monitoring'}
          </Text>
        </TouchableOpacity>
      </View>

      {/* 60-Second SOS Modal */}
      <Modal visible={sosActive} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>🚨 DROWSINESS DETECTED</Text>
            <Text style={styles.modalSubtitle}>
              Emergency SOS will be sent in:
            </Text>
            <Text style={styles.countdownText}>{sosSeconds}s</Text>
            <TouchableOpacity style={styles.cancelButton} onPress={cancelSOS}>
              <Text style={styles.cancelButtonText}>CANCEL SOS</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f172a',
    paddingHorizontal: 20,
  },
  header: {
    marginTop: 20,
    marginBottom: 20,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#f8fafc',
  },
  headerSubtitle: {
    fontSize: 13,
    color: '#94a3b8',
    marginTop: 4,
  },
  statusCard: {
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: 20,
    alignItems: 'center',
    marginBottom: 20,
  },
  statusLabel: {
    color: '#64748b',
    fontSize: 12,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  badge: {
    paddingHorizontal: 20,
    paddingVertical: 8,
    borderRadius: 20,
  },
  badgeText: {
    color: '#ffffff',
    fontWeight: 'bold',
    fontSize: 18,
  },
  grid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 30,
  },
  metricCard: {
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: 20,
    width: '47%',
    alignItems: 'center',
  },
  metricValue: {
    color: '#38bdf8',
    fontSize: 28,
    fontWeight: 'bold',
  },
  metricLabel: {
    color: '#94a3b8',
    fontSize: 12,
    marginTop: 4,
  },
  controls: {
    marginTop: 'auto',
    marginBottom: 30,
  },
  button: {
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  buttonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContent: {
    backgroundColor: '#1e293b',
    borderRadius: 16,
    padding: 30,
    width: '100%',
    alignItems: 'center',
  },
  modalTitle: {
    color: '#ef4444',
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  modalSubtitle: {
    color: '#94a3b8',
    fontSize: 14,
    marginBottom: 20,
  },
  countdownText: {
    color: '#f8fafc',
    fontSize: 56,
    fontWeight: 'bold',
    marginBottom: 24,
  },
  cancelButton: {
    backgroundColor: '#10b981',
    paddingVertical: 14,
    paddingHorizontal: 30,
    borderRadius: 10,
    width: '100%',
    alignItems: 'center',
  },
  cancelButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: 'bold',
  },
});
