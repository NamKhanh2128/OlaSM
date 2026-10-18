import 'dart:math' as math;
import 'package:flutter/material.dart';

/// Custom painter that draws animated audio waveform bars.
/// Used inside DynamicOrbVisualizer and standalone.
class AudioWaveformPainter extends CustomPainter {
  final double audioLevel; // 0.0 – 1.0
  final Color color;
  final int barCount;
  final double animationValue; // 0.0 – 1.0 from AnimationController

  const AudioWaveformPainter({
    required this.audioLevel,
    required this.color,
    this.barCount = 24,
    this.animationValue = 0.0,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.fill;

    final barWidth = (size.width / barCount) * 0.6;
    final spacing = size.width / barCount;

    for (int i = 0; i < barCount; i++) {
      // Animated height: combine audio level + sine wave offset per bar
      final phase = (i / barCount) * math.pi * 2;
      final wave = math.sin(phase + animationValue * math.pi * 2);
      final rawHeight = (audioLevel * 0.7 + wave * 0.3 * audioLevel + 0.05);
      final barHeight = (rawHeight.clamp(0.05, 1.0) * size.height);

      final x = spacing * i + (spacing - barWidth) / 2;
      final top = (size.height - barHeight) / 2;

      final rRect = RRect.fromRectAndRadius(
        Rect.fromLTWH(x, top, barWidth, barHeight),
        Radius.circular(barWidth / 2),
      );
      canvas.drawRRect(rRect, paint);
    }
  }

  @override
  bool shouldRepaint(AudioWaveformPainter oldDelegate) =>
      oldDelegate.audioLevel != audioLevel ||
      oldDelegate.animationValue != animationValue;
}

/// Standalone animated waveform widget for embedding in the voice screen.
class AudioWaveformWidget extends StatefulWidget {
  final double audioLevel;
  final Color color;
  final double width;
  final double height;

  const AudioWaveformWidget({
    super.key,
    required this.audioLevel,
    this.color = const Color(0xFF00E676),
    this.width = 200,
    this.height = 40,
  });

  @override
  State<AudioWaveformWidget> createState() => _AudioWaveformWidgetState();
}

class _AudioWaveformWidgetState extends State<AudioWaveformWidget>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (_, __) => CustomPaint(
        size: Size(widget.width, widget.height),
        painter: AudioWaveformPainter(
          audioLevel: widget.audioLevel,
          color: widget.color,
          animationValue: _controller.value,
        ),
      ),
    );
  }
}
