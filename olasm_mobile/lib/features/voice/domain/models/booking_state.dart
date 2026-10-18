/// Represents taxi booking data synced in real-time from the backend/LiveKit Agent.
class BookingState {
  final String? bookingId;
  final String? customerName;
  final String? phoneNumber;
  final String? pickupLocation;
  final String? dropoffLocation;
  final String? vehicleType; // e.g. "4 chỗ", "7 chỗ", "xe máy"
  final double? estimatedPrice;
  final String? currency;
  final String status; // "collecting", "confirmed", "dispatching", "cancelled"
  final Map<String, dynamic> rawPayload;

  const BookingState({
    this.bookingId,
    this.customerName,
    this.phoneNumber,
    this.pickupLocation,
    this.dropoffLocation,
    this.vehicleType,
    this.estimatedPrice,
    this.currency = 'VND',
    this.status = 'collecting',
    this.rawPayload = const {},
  });

  bool get hasRoute =>
      pickupLocation != null &&
      pickupLocation!.isNotEmpty &&
      dropoffLocation != null &&
      dropoffLocation!.isNotEmpty;

  factory BookingState.fromDataChannel(Map<String, dynamic> json) {
    // Support nested OlaSM public_state() structure as well as flat format
    final pickupMap = json['pickup'] is Map<String, dynamic> ? json['pickup'] as Map<String, dynamic> : null;
    final destMap = json['destination'] is Map<String, dynamic> ? json['destination'] as Map<String, dynamic> : null;
    final quoteMap = json['quote'] is Map<String, dynamic> ? json['quote'] as Map<String, dynamic> : null;
    final bookingMap = json['booking'] is Map<String, dynamic> ? json['booking'] as Map<String, dynamic> : null;

    final pickup = json['pickup_location'] as String? ?? pickupMap?['display_name'] as String? ?? pickupMap?['address'] as String?;
    final dropoff = json['dropoff_location'] as String? ?? destMap?['display_name'] as String? ?? destMap?['address'] as String?;

    final num? priceNum = (json['estimated_price'] ?? quoteMap?['fare_amount'] ?? bookingMap?['estimated_fare']) as num?;
    final String? bId = json['booking_id'] as String? ?? bookingMap?['booking_id'] as String?;
    final String statusStr = json['status'] as String? ?? bookingMap?['status'] as String? ?? json['confirmation_status'] as String? ?? 'collecting';

    return BookingState(
      bookingId: bId,
      customerName: json['customer_name'] as String?,
      phoneNumber: json['phone_number'] as String?,
      pickupLocation: pickup,
      dropoffLocation: dropoff,
      vehicleType: json['vehicle_type'] as String?,
      estimatedPrice: priceNum?.toDouble(),
      currency: (quoteMap?['currency'] ?? json['currency'] ?? 'VND') as String,
      status: statusStr,
      rawPayload: json,
    );
  }

  BookingState copyWith({
    String? bookingId,
    String? customerName,
    String? phoneNumber,
    String? pickupLocation,
    String? dropoffLocation,
    String? vehicleType,
    double? estimatedPrice,
    String? currency,
    String? status,
    Map<String, dynamic>? rawPayload,
  }) {
    return BookingState(
      bookingId: bookingId ?? this.bookingId,
      customerName: customerName ?? this.customerName,
      phoneNumber: phoneNumber ?? this.phoneNumber,
      pickupLocation: pickupLocation ?? this.pickupLocation,
      dropoffLocation: dropoffLocation ?? this.dropoffLocation,
      vehicleType: vehicleType ?? this.vehicleType,
      estimatedPrice: estimatedPrice ?? this.estimatedPrice,
      currency: currency ?? this.currency,
      status: status ?? this.status,
      rawPayload: rawPayload ?? this.rawPayload,
    );
  }
}
