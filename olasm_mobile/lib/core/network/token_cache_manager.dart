import 'dart:async';
import 'package:dio/dio.dart';
import 'package:uuid/uuid.dart';
import '../config/app_config.dart';

/// Connection credentials returned by backend
class MobileVoiceCredentials {
  final String serverUrl;
  final String participantToken;
  final String roomName;
  final String agentName;
  final int tokenTtlSeconds;
  final DateTime issuedAt;

  MobileVoiceCredentials({
    required this.serverUrl,
    required this.participantToken,
    required this.roomName,
    required this.agentName,
    required this.tokenTtlSeconds,
    required this.issuedAt,
  });

  bool get isExpired {
    // Refresh proactively 2 minutes before expiry
    final expiration = issuedAt.add(Duration(seconds: tokenTtlSeconds - 120));
    return DateTime.now().isAfter(expiration);
  }

  factory MobileVoiceCredentials.fromJson(Map<String, dynamic> json) {
    return MobileVoiceCredentials(
      serverUrl: json['server_url'] as String,
      participantToken: json['participant_token'] as String,
      roomName: json['room_name'] as String,
      agentName: json['agent_name'] as String,
      tokenTtlSeconds: json['token_ttl_seconds'] as int? ?? 900,
      issuedAt: DateTime.now(),
    );
  }
}

/// TokenPool: Maintains a fresh LiveKit token in memory at all times.
/// When WakeWord or Push-to-Talk triggers, token is returned in 0ms without waiting
/// for a network round-trip.
class TokenCacheManager {
  final Dio _dio;
  final String _backendUrl;
  final String _deviceId;

  MobileVoiceCredentials? _cachedCredentials;
  Timer? _refreshTimer;
  bool _isFetching = false;

  TokenCacheManager({
    Dio? dio,
    String? backendUrl,
    String? deviceId,
  })  : _dio = dio ?? Dio(),
        _backendUrl = backendUrl ?? AppConfig.defaultBackendUrl,
        _deviceId = deviceId ?? const Uuid().v4();

  String get deviceId => _deviceId;

  /// Warm up the token cache on app startup
  Future<void> warmup() async {
    if (_cachedCredentials != null && !_cachedCredentials!.isExpired) {
      return;
    }
    await _fetchNewToken(triggerSource: 'warmup');
  }

  /// Get credentials immediately (0ms). If cache is empty or stale, fetches async.
  Future<MobileVoiceCredentials> getCredentials({
    String triggerSource = 'push_to_talk',
    double? confidence,
  }) async {
    if (_cachedCredentials != null && !_cachedCredentials!.isExpired) {
      final creds = _cachedCredentials!;
      // Trigger background replenishment for the next call
      _scheduleBackgroundRefresh();
      return creds;
    }

    return await _fetchNewToken(
      triggerSource: triggerSource,
      confidence: confidence,
    );
  }

  Future<MobileVoiceCredentials> _fetchNewToken({
    String triggerSource = 'push_to_talk',
    double? confidence,
  }) async {
    if (_isFetching) {
      // Wait a short time for concurrent fetch
      for (int i = 0; i < 20; i++) {
        await Future.delayed(const Duration(milliseconds: 50));
        if (_cachedCredentials != null && !_cachedCredentials!.isExpired) {
          return _cachedCredentials!;
        }
      }
    }

    _isFetching = true;
    try {
      final response = await _dio.post(
        '$_backendUrl/api/v1/mobile/voice-token',
        data: {
          'device_id': _deviceId,
          'trigger_source': triggerSource,
          if (confidence != null) 'wake_word_confidence': confidence,
        },
        options: Options(
          headers: {'Content-Type': 'application/json'},
          sendTimeout: const Duration(seconds: 4),
          receiveTimeout: const Duration(seconds: 4),
        ),
      );

      final creds = MobileVoiceCredentials.fromJson(response.data);
      _cachedCredentials = creds;
      _scheduleAutoRefresh(creds.tokenTtlSeconds);
      return creds;
    } finally {
      _isFetching = false;
    }
  }

  void _scheduleAutoRefresh(int ttlSeconds) {
    _refreshTimer?.cancel();
    // Refresh 2 minutes before expiry
    final refreshDelay = Duration(seconds: (ttlSeconds > 180 ? ttlSeconds - 120 : ttlSeconds ~/ 2));
    _refreshTimer = Timer(refreshDelay, () {
      _fetchNewToken(triggerSource: 'auto_refresh');
    });
  }

  void _scheduleBackgroundRefresh() {
    Future.microtask(() async {
      try {
        await _fetchNewToken(triggerSource: 'pool_replenish');
      } catch (_) {
        // Silently handle background refresh failures
      }
    });
  }

  void dispose() {
    _refreshTimer?.cancel();
  }
}
