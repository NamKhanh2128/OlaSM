import 'dart:async';
import 'dart:typed_data';
import 'package:flutter/services.dart';

class WakeWordDetectionEvent {
  final double score;
  final String keyword;
  final int timestampMs;

  WakeWordDetectionEvent({
    required this.score,
    required this.keyword,
    required this.timestampMs,
  });

  factory WakeWordDetectionEvent.fromMap(Map<dynamic, dynamic> map) {
    return WakeWordDetectionEvent(
      score: (map['score'] as num?)?.toDouble() ?? 0.0,
      keyword: map['keyword'] as String? ?? 'hey_olasm',
      timestampMs: map['timestamp'] as int? ?? DateTime.now().millisecondsSinceEpoch,
    );
  }
}

/// NativeWakeWordBridge: Communicates with native Android (Kotlin) / iOS (Swift)
/// wake word engine running on-device ONNX runtime.
class NativeWakeWordBridge {
  static const MethodChannel _methodChannel = MethodChannel('com.olasm.mobile/wakeword');
  static const EventChannel _eventChannel = EventChannel('com.olasm.mobile/wakeword_events');

  Stream<WakeWordDetectionEvent>? _detectionStream;

  /// Initialize native ONNX model and audio recorder
  Future<bool> initialize({
    String modelAssetPath = 'assets/models/hey_olasm_int8.onnx',
    double threshold = 0.68,
  }) async {
    try {
      final result = await _methodChannel.invokeMethod<bool>('initialize', {
        'modelPath': modelAssetPath,
        'threshold': threshold,
      });
      return result ?? false;
    } on MissingPluginException {
      // In development or when native module is mocked
      return false;
    } catch (_) {
      return false;
    }
  }

  /// Start on-device listening
  Stream<WakeWordDetectionEvent> startListening() {
    _detectionStream ??= _eventChannel
        .receiveBroadcastStream()
        .map((event) => WakeWordDetectionEvent.fromMap(event as Map<dynamic, dynamic>));

    _methodChannel.invokeMethod('startListening').catchError((_) => null);
    return _detectionStream!;
  }

  /// Temporarily pause listening while LiveKit voice session is active
  Future<void> pauseListening() async {
    try {
      await _methodChannel.invokeMethod('pauseListening');
    } catch (_) {}
  }

  /// Resume listening when voice session finishes
  Future<void> resumeListening() async {
    try {
      await _methodChannel.invokeMethod('resumeListening');
    } catch (_) {}
  }

  /// Retrieve the 500ms pre-roll PCM frames captured before the trigger
  Future<List<Uint8List>> getPreRollAudioBuffer() async {
    try {
      final List<dynamic>? frames = await _methodChannel.invokeMethod<List<dynamic>>('getPreRollBuffer');
      if (frames == null) return [];
      return frames.cast<Uint8List>();
    } catch (_) {
      return [];
    }
  }

  Future<void> dispose() async {
    try {
      await _methodChannel.invokeMethod('dispose');
    } catch (_) {}
  }
}
