import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/token_cache_manager.dart';
import '../../data/livekit_transport.dart';
import '../../data/native_wakeword_bridge.dart';
import '../models/voice_session_state.dart';

final tokenCacheProvider = Provider<TokenCacheManager>((ref) {
  final manager = TokenCacheManager();
  manager.warmup(); // Warm up credentials on startup
  ref.onDispose(() => manager.dispose());
  return manager;
});

final nativeWakeWordProvider = Provider<NativeWakeWordBridge>((ref) {
  final bridge = NativeWakeWordBridge();
  ref.onDispose(() => bridge.dispose());
  return bridge;
});

final voiceSessionProvider = StateNotifierProvider<VoiceSessionController, VoiceSessionState>((ref) {
  final tokenManager = ref.watch(tokenCacheProvider);
  final wakeBridge = ref.watch(nativeWakeWordProvider);
  return VoiceSessionController(tokenManager, wakeBridge);
});

class VoiceSessionController extends StateNotifier<VoiceSessionState> {
  final TokenCacheManager _tokenManager;
  final NativeWakeWordBridge _wakeBridge;
  final LiveKitTransport _transport = LiveKitTransport();

  StreamSubscription? _wakeWordSubscription;

  VoiceSessionController(this._tokenManager, this._wakeBridge)
      : super(const VoiceSessionState()) {
    _initTransportCallbacks();
    _initWakeWord();
  }

  void _initTransportCallbacks() {
    _transport.onAudioLevel = (level) {
      state = state.copyWith(audioLevel: level);
    };

    _transport.onTranscript = (text, isFinal, isAgent) {
      if (isAgent) {
        state = state.copyWith(
          lastAgentUtterance: text,
          status: isFinal ? VoiceSessionStatus.connected : VoiceSessionStatus.agentSpeaking,
        );
      } else {
        state = state.copyWith(
          currentTranscript: text,
          status: isFinal ? VoiceSessionStatus.connected : VoiceSessionStatus.userSpeaking,
        );
      }
    };

    _transport.onBookingUpdate = (booking) {
      state = state.copyWith(booking: booking);
    };

    _transport.onDisconnected = () {
      _onSessionEnded();
    };
  }

  Future<void> _initWakeWord() async {
    final initialized = await _wakeBridge.initialize();
    if (initialized) {
      _startWakeWordListening();
    }
  }

  void _startWakeWordListening() {
    _wakeWordSubscription?.cancel();
    _wakeWordSubscription = _wakeBridge.startListening().listen((event) {
      debugPrint('WakeWord detected: ${event.keyword} score: ${event.score}');
      state = state.copyWith(wakeWordConfidence: event.score);
      // Trigger instant hands-free session
      startVoiceSession(triggerSource: 'wake_word', confidence: event.score);
    });
  }

  /// Start voice session triggered by WakeWord or Push-to-Talk button
  Future<void> startVoiceSession({
    String triggerSource = 'push_to_talk',
    double? confidence,
  }) async {
    if (state.isActive || state.status == VoiceSessionStatus.connecting) return;

    state = state.copyWith(
      status: VoiceSessionStatus.connecting,
      errorMessage: null,
    );

    try {
      // 1. Pause native wake word inference to release audio processing
      await _wakeBridge.pauseListening();

      // 2. Fetch pre-roll buffer in parallel with token acquisition
      final preRollFuture = _wakeBridge.getPreRollAudioBuffer();
      final credsFuture = _tokenManager.getCredentials(
        triggerSource: triggerSource,
        confidence: confidence,
      );

      final results = await Future.wait([credsFuture, preRollFuture]);
      final credentials = results[0] as MobileVoiceCredentials;
      final preRollFrames = results[1] as List<Uint8List>;

      // 3. Connect to LiveKit Room
      await _transport.connect(credentials);

      // 4. Flush pre-roll buffer immediately over LiveKit data channel
      if (preRollFrames.isNotEmpty) {
        await _transport.flushPreConnectBuffer(preRollFrames);
      }

      state = state.copyWith(
        status: VoiceSessionStatus.connected,
        roomName: credentials.roomName,
        activeAgentName: credentials.agentName,
      );
    } catch (e) {
      state = state.copyWith(
        status: VoiceSessionStatus.error,
        errorMessage: 'Không thể kết nối tổng đài: $e',
      );
      // Resume wake word on failure
      await _wakeBridge.resumeListening();
    }
  }

  /// End current voice call
  Future<void> endVoiceSession() async {
    if (state.status == VoiceSessionStatus.idle) return;

    state = state.copyWith(status: VoiceSessionStatus.disconnecting);
    await _transport.disconnect();
    _onSessionEnded();
  }

  void _onSessionEnded() {
    state = state.copyWith(
      status: VoiceSessionStatus.idle,
      audioLevel: 0.0,
      currentTranscript: null,
    );
    // Resume listening for "Hey OlaSM"
    _wakeBridge.resumeListening();
  }

  @override
  void dispose() {
    _wakeWordSubscription?.cancel();
    _transport.disconnect();
    super.dispose();
  }
}
