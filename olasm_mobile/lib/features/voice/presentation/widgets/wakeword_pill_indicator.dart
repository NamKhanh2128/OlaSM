import 'package:flutter/material.dart';

/// Small pill indicator showing wake word listening status and confidence score.
class WakeWordPillIndicator extends StatefulWidget {
  final bool isListening;
  final double confidence;

  const WakeWordPillIndicator({
    super.key,
    required this.isListening,
    this.confidence = 0.0,
  });

  @override
  State<WakeWordPillIndicator> createState() => _WakeWordPillIndicatorState();
}

class _WakeWordPillIndicatorState extends State<WakeWordPillIndicator>
    with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);

    _pulseAnimation = Tween<double>(begin: 0.5, end: 1.0).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
      decoration: BoxDecoration(
        color: widget.isListening
            ? const Color(0xFF00E676).withOpacity(0.12)
            : Colors.white.withOpacity(0.06),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: widget.isListening
              ? const Color(0xFF00E676).withOpacity(0.4)
              : Colors.white24,
          width: 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Animated dot
          AnimatedBuilder(
            animation: _pulseAnimation,
            builder: (_, __) => Opacity(
              opacity: widget.isListening ? _pulseAnimation.value : 0.4,
              child: Container(
                width: 7,
                height: 7,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: widget.isListening
                      ? const Color(0xFF00E676)
                      : Colors.white38,
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
          Text(
            widget.isListening
                ? "Đang nghe: 'Hey OlaSM'"
                : "Tạm dừng nghe",
            style: TextStyle(
              color: widget.isListening ? Colors.white : Colors.white54,
              fontSize: 12,
              fontWeight: FontWeight.w500,
              letterSpacing: 0.2,
            ),
          ),
        ],
      ),
    );
  }
}
