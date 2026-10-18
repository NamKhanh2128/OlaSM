import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../../domain/models/booking_state.dart';

/// Interactive vector map widget that renders pickup, destination,
/// calculated route path, and animated moving taxi vehicle.
class BookingMapWidget extends StatefulWidget {
  final BookingState booking;
  final double height;

  const BookingMapWidget({
    super.key,
    required this.booking,
    this.height = 220,
  });

  @override
  State<BookingMapWidget> createState() => _BookingMapWidgetState();
}

class _BookingMapWidgetState extends State<BookingMapWidget>
    with SingleTickerProviderStateMixin {
  late AnimationController _animController;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 4),
    )..repeat();
  }

  @override
  void dispose() {
    _animController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.booking.hasRoute && widget.booking.pickupLocation == null) {
      return const SizedBox.shrink();
    }

    final isDispatching = widget.booking.status == 'dispatching';
    final isConfirmed = widget.booking.status == 'confirmed';

    return Container(
      height: widget.height,
      margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFF131722),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(
          color: const Color(0xFF00E676).withOpacity(0.25),
          width: 1.2,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.45),
            blurRadius: 18,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Stack(
        children: [
          // Background stylized road grid
          Positioned.fill(
            child: CustomPaint(
              painter: _MapGridPainter(),
            ),
          ),

          // Route polyline and moving vehicle painter
          Positioned.fill(
            child: AnimatedBuilder(
              animation: _animController,
              builder: (context, child) {
                return CustomPaint(
                  painter: _RoutePathPainter(
                    progress: _animController.value,
                    isMoving: isDispatching || isConfirmed,
                  ),
                );
              },
            ),
          ),

          // Pickup Location Marker (Left / Bottom-Left)
          Positioned(
            left: 28,
            bottom: 40,
            child: _LocationPin(
              title: widget.booking.pickupLocation ?? 'Điểm đón',
              color: const Color(0xFF00E676),
              icon: Icons.my_location_rounded,
              isPickup: true,
            ),
          ),

          // Destination Location Marker (Right / Top-Right)
          Positioned(
            right: 28,
            top: 36,
            child: _LocationPin(
              title: widget.booking.dropoffLocation ?? 'Điểm đến',
              color: const Color(0xFFFF5252),
              icon: Icons.location_on_rounded,
              isPickup: false,
            ),
          ),

          // Live Route Badge Overlay (ETA & Distance)
          Positioned(
            top: 14,
            left: 16,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: const Color(0xFF1E222D).withOpacity(0.9),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.white12),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: const BoxDecoration(
                      color: Color(0xFF00E676),
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 6),
                  const Text(
                    'Lộ trình thời gian thực',
                    style: TextStyle(
                      color: Colors.white70,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _LocationPin extends StatelessWidget {
  final String title;
  final Color color;
  final IconData icon;
  final bool isPickup;

  const _LocationPin({
    required this.title,
    required this.color,
    required this.icon,
    required this.isPickup,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment:
          isPickup ? CrossAxisAlignment.start : CrossAxisAlignment.end,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          constraints: const BoxConstraints(maxWidth: 130),
          decoration: BoxDecoration(
            color: const Color(0xFF1A1E2A).withOpacity(0.95),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: color.withOpacity(0.4)),
            boxShadow: [
              BoxShadow(
                color: color.withOpacity(0.2),
                blurRadius: 8,
              ),
            ],
          ),
          child: Text(
            title,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 10,
              fontWeight: FontWeight.bold,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
        const SizedBox(height: 4),
        Container(
          width: 30,
          height: 30,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: color.withOpacity(0.5),
                blurRadius: 10,
                spreadRadius: 2,
              ),
            ],
          ),
          child: Icon(icon, color: Colors.black87, size: 16),
        ),
      ],
    );
  }
}

class _MapGridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white.withOpacity(0.04)
      ..strokeWidth = 1.0;

    const step = 28.0;
    for (double x = 0; x < size.width; x += step) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }
    for (double y = 0; y < size.height; y += step) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _RoutePathPainter extends CustomPainter {
  final double progress;
  final bool isMoving;

  _RoutePathPainter({
    required this.progress,
    required this.isMoving,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final start = Offset(42, size.height - 45);
    final end = Offset(size.width - 42, 60);

    // Curved Bezier route path
    final controlPoint1 = Offset(size.width * 0.25, size.height * 0.15);
    final controlPoint2 = Offset(size.width * 0.65, size.height * 0.90);

    final path = Path()
      ..moveTo(start.dx, start.dy)
      ..cubicTo(
        controlPoint1.dx,
        controlPoint1.dy,
        controlPoint2.dx,
        controlPoint2.dy,
        end.dx,
        end.dy,
      );

    // Draw route background line
    final bgPaint = Paint()
      ..color = const Color(0xFF00E676).withOpacity(0.2)
      ..strokeWidth = 5.0
      ..style = PaintingStyle.stroke;
    canvas.drawPath(path, bgPaint);

    // Draw active glowing path
    final routePaint = Paint()
      ..shader = const LinearGradient(
        colors: [Color(0xFF00E676), Color(0xFF00B0FF)],
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height))
      ..strokeWidth = 3.5
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawPath(path, routePaint);

    // Draw animated moving vehicle position along Bezier curve
    if (isMoving) {
      final t = progress;
      // Cubic Bezier formula: B(t) = (1-t)^3*P0 + 3(1-t)^2*t*P1 + 3(1-t)*t^2*P2 + t^3*P3
      final double carX = math.pow(1 - t, 3) * start.dx +
          3 * math.pow(1 - t, 2) * t * controlPoint1.dx +
          3 * (1 - t) * math.pow(t, 2) * controlPoint2.dx +
          math.pow(t, 3) * end.dx;
      final double carY = math.pow(1 - t, 3) * start.dy +
          3 * math.pow(1 - t, 2) * t * controlPoint1.dy +
          3 * (1 - t) * math.pow(t, 2) * controlPoint2.dy +
          math.pow(t, 3) * end.dy;

      final carCenter = Offset(carX, carY);

      // Glowing dot for moving vehicle
      final carGlowPaint = Paint()
        ..color = const Color(0xFF00E676).withOpacity(0.4)
        ..style = PaintingStyle.fill;
      canvas.drawCircle(carCenter, 14, carGlowPaint);

      final carPaint = Paint()
        ..color = Colors.white
        ..style = PaintingStyle.fill;
      canvas.drawCircle(carCenter, 6, carPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _RoutePathPainter oldDelegate) {
    return oldDelegate.progress != progress || oldDelegate.isMoving != isMoving;
  }
}
