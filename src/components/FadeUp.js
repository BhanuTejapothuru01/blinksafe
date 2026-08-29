/**
 * BlinkSafe Premium Mobile UI — FadeUp Component
 * Staggered fade and slide-up card/element animation.
 */

import React, { useEffect, useRef } from 'react';
import { Animated } from 'react-native';
import { motion } from '../theme/animations';

export default function FadeUp({
  children,
  delay = 0,
  duration = motion.durations.normal,
  style,
}) {
  const translateY = useRef(new Animated.Value(20)).current;
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
    <Animated.View style={[{ transform: [{ translateY }], opacity }, style]}>
      {children}
    </Animated.View>
  );
}
