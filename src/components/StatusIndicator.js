/**
 * BlinkSafe Premium Mobile UI — StatusIndicator Component
 * Animated state badge component for alertness states (SAFE, ALERT, DROWSY, DANGER, SOS).
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors } from '../theme/colors';

export default function StatusIndicator({ state = 'SAFE' }) {
  const getStatusColor = () => {
    switch (state) {
      case 'DANGER':
        return colors.danger;
      case 'DROWSY':
        return colors.drowsy;
      case 'ALERT':
        return colors.alert;
      case 'SOS':
        return colors.sos;
      default:
        return colors.safe;
    }
  };

  return (
    <View style={[styles.badge, { backgroundColor: getStatusColor() }]}>
      <Text style={styles.text}>{state}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: 20,
    paddingVertical: 8,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  text: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '800',
    letterSpacing: 1,
  },
});
