/**
 * BlinkSafe Premium Mobile UI — MaskedTextReveal Component
 * Masked text entrance animation component. Animates translateY & opacity smoothly.
 */

import React, { useEffect, useRef } from 'react';
import { Animated, View, StyleSheet } from 'react-native';
import { motion } from '../theme/animations';

export default function MaskedTextReveal({
  children,
  delay = 0,
  duration = motion.durations.slow,
  style,
}) {
  const translateY = useRef(new Animated.Value(30)).current;
  const opacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(translateY, {
        toValue: 0,
        duration: duration,
        delay: delay,
        useNativeDriver: true,
      }),
      Animated.timing(opacity, {
        toValue: 1,
        duration: duration,
        delay: delay,
        useNativeDriver: true,
      }),
    ]).start();
  }, [delay, duration, opacity, translateY]);

  return (
    <View style={styles.container}>
      <Animated.View style={[{ transform: [{ translateY }], opacity }, style]}>
        {children}
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    overflow: 'hidden',
  },
});
