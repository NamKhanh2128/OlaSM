import 'package:flutter/material.dart';
import '../../domain/models/booking_state.dart';

/// Real-time booking card displaying pickup, destination, vehicle type, and estimated fare.
class BookingCardWidget extends StatelessWidget {
  final BookingState booking;

  const BookingCardWidget({
    super.key,
    required this.booking,
  });

  @override
  Widget build(BuildContext context) {
    if (!booking.hasRoute && booking.pickupLocation == null) {
      return const SizedBox.shrink();
    }

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFF1E222D).withOpacity(0.92),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: const Color(0xFF00E676).withOpacity(0.3),
          width: 1.2,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.4),
            blurRadius: 18,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  const Icon(Icons.local_taxi_rounded, color: Color(0xFF00E676), size: 22),
                  const SizedBox(width: 8),
                  Text(
                    booking.vehicleType ?? 'Xe 4 chỗ',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              _buildStatusBadge(booking.status),
            ],
          ),
          const Divider(color: Colors.white12, height: 24),
          _buildLocationRow(
            icon: Icons.my_location_rounded,
            iconColor: const Color(0xFF00E676),
            title: 'Điểm đón',
            address: booking.pickupLocation ?? 'Đang nhận diện...',
          ),
          const SizedBox(height: 12),
          _buildLocationRow(
            icon: Icons.location_on_rounded,
            iconColor: const Color(0xFFFF5252),
            title: 'Điểm đến',
            address: booking.dropoffLocation ?? 'Chờ khách cung cấp...',
          ),
          if (booking.estimatedPrice != null) ...[
            const Divider(color: Colors.white12, height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Giá cước ước tính',
                  style: TextStyle(color: Colors.white60, fontSize: 13),
                ),
                Text(
                  '${_formatCurrency(booking.estimatedPrice!)} ${booking.currency}',
                  style: const TextStyle(
                    color: Color(0xFF00E676),
                    fontSize: 17,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildStatusBadge(String status) {
    Color badgeColor;
    String label;

    switch (status) {
      case 'confirmed':
        badgeColor = const Color(0xFF00E676);
        label = 'Đã xác nhận';
        break;
      case 'dispatching':
        badgeColor = const Color(0xFFFFB300);
        label = 'Đang tìm tài xế';
        break;
      default:
        badgeColor = const Color(0xFF00B0FF);
        label = 'Đang tiếp nhận';
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: badgeColor.withOpacity(0.18),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: badgeColor.withOpacity(0.4)),
      ),
      child: Text(
        label,
        style: TextStyle(color: badgeColor, fontSize: 12, fontWeight: FontWeight.w600),
      ),
    );
  }

  Widget _buildLocationRow({
    required IconData icon,
    required Color iconColor,
    required String title,
    required String address,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: iconColor, size: 18),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(color: Colors.white54, fontSize: 11),
              ),
              const SizedBox(height: 2),
              Text(
                address,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ],
    );
  }

  String _formatCurrency(double amount) {
    return amount.toStringAsFixed(0).replaceAllMapped(
          RegExp(r'(\d{1,3})(?=(\d{3})+(?!\d))'),
          (Match m) => '${m[1]}.',
        );
  }
}
