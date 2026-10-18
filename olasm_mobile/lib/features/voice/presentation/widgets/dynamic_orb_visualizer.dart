import 'package:flutter/material.dart';

/// Dynamic sound-wave glowing orb that pulses in response to user/agent speech.
class DynamicOrbVisualizer extends StatelessWidget {
  final double audioLevel;
  final bool isActive;
  final bool isAgentSpeaking;

  const DynamicOrbVisualizer({
    super.key,
    required this.audioLevel,
    required this.isActive,
    this.isAgentSpeaking = false,
  });

  @override
  Widget build(BuildContext context) {
    // Dynamic scale based on mic audio level
    final double scale = 1.0 + (audioLevel.clamp(0.0, 1.0) * 0.4);

    final Color primaryGlow = isAgentSpeaking
        ? const Color(0xFF00E676) // Green SM Emerald
        : const Color(0xFF00B0FF); // Electric Blue

    final Color secondaryGlow = isAgentSpeaking
        ? const Color(0xFF1DE9B6)
        : const Color(0xFF7C4DFF);

    return AnimatedScale(
      scale: isActive ? scale : 1.0,
      duration: const Duration(milliseconds: 80),
      curve: Curves.easeOutCubic,
      child: Container(
        width: 180,
        height: 180,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: RadialGradient(
            colors: [
              Colors.white,
              primaryGlow.withOpacity(0.9),
              secondaryGlow.withOpacity(0.6),
              Colors.transparent,
            ],
            stops: const [0.0, 0.4, 0.7, 1.0],
          ),
          boxShadow: [
            BoxShadow(
              color: primaryGlow.withOpacity(isActive ? 0.7 : 0.2),
              blurRadius: isActive ? 45 : 15,
              spreadRadius: isActive ? 15 : 2,
            ),
          ],
        ),
        child: Center(
          child: Icon(
            isAgentSpeaking
                ? Icons.graphic_eq_rounded
                : (isActive ? Icons.mic_rounded : Icons.mic_none_rounded),
            size: 54,
            color: Colors.white,
          ),
        ),
      ),
    );
  }
}
