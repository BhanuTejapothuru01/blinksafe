/**
 * BlinkSafe Premium Mobile UI — AnimatedButton Component
 * Tactile scale feedback button component for high-performance touch feedback.
 */

import React, { useRef } from 'react';
import { Animated, TouchableWithoutFeedback, Text, StyleSheet } from 'react-native';
import { colors } from '../theme/colors';
import { motion } from '../theme/animations';

export default function AnimatedButton({
  title,
  onPress,
  variant = 'primary',
  style,
  textStyle,
}) {
  const scale = useRef(new Animated.Value(1.0)).current;

  const handlePressIn = () => {
    Animated.timing(scale, {
      toValue: 0.96,
      duration: motion.durations.fast,
      useNativeDriver: true,
    }).start();
  };

  const handlePressOut = () => {
    Animated.timing(scale, {
      toValue: 1.0,
      duration: motion.durations.fast,
      useNativeDriver: true,
    }).start();
  };

  const getBackgroundColor = () => {
    if (variant === 'danger') return colors.danger;
    if (variant === 'secondary') return colors.surfaceLight;
    return colors.primary;
  };

  return (
    <TouchableWithoutFeedback
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
      onPress={onPress}
    >
      <Animated.View
        style={[
          styles.button,
          { backgroundColor: getBackgroundColor(), transform: [{ scale }] },
          style,
        ]}
      >
        <Text style={[styles.text, textStyle]}>{title}</Text>
      </Animated.View>
    </TouchableWithoutFeedback>
  );
}

const styles = StyleSheet.create({
  button: {
    paddingVertical: 16,
    paddingHorizontal: 24,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  text: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
});
