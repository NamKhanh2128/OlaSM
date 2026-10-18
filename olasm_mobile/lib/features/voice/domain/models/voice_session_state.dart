import 'booking_state.dart';

enum VoiceSessionStatus {
  idle,             // Listening for wake word or awaiting user action
  connecting,       // WebRTC ICE negotiation & room join in progress
  connected,        // Active voice conversation
  agentSpeaking,    // Agent is responding with audio
  userSpeaking,     // VAD indicates user is currently talking
  disconnecting,    // Closing session
  error,            // Session encountered a failure
}

class VoiceSessionState {
  final VoiceSessionStatus status;
  final String? roomName;
  final String? activeAgentName;
  final String? currentTranscript;
  final String? lastAgentUtterance;
  final BookingState booking;
  final double audioLevel; // 0.0 to 1.0 for UI visualizer
  final String? errorMessage;
  final bool isWakeWordListening;
  final double wakeWordConfidence;

  const VoiceSessionState({
    this.status = VoiceSessionStatus.idle,
    this.roomName,
    this.activeAgentName,
    this.currentTranscript,
    this.lastAgentUtterance,
    this.booking = const BookingState(),
    this.audioLevel = 0.0,
    this.errorMessage,
    this.isWakeWordListening = true,
    this.wakeWordConfidence = 0.0,
  });

  bool get isActive =>
      status == VoiceSessionStatus.connected ||
      status == VoiceSessionStatus.agentSpeaking ||
      status == VoiceSessionStatus.userSpeaking;

  VoiceSessionState copyWith({
    VoiceSessionStatus? status,
    String? roomName,
    String? activeAgentName,
    String? currentTranscript,
    String? lastAgentUtterance,
    BookingState? booking,
    double? audioLevel,
    String? errorMessage,
    bool? isWakeWordListening,
    double? wakeWordConfidence,
  }) {
    return VoiceSessionState(
      status: status ?? this.status,
      roomName: roomName ?? this.roomName,
      activeAgentName: activeAgentName ?? this.activeAgentName,
      currentTranscript: currentTranscript ?? this.currentTranscript,
      lastAgentUtterance: lastAgentUtterance ?? this.lastAgentUtterance,
      booking: booking ?? this.booking,
      audioLevel: audioLevel ?? this.audioLevel,
      errorMessage: errorMessage ?? this.errorMessage,
      isWakeWordListening: isWakeWordListening ?? this.isWakeWordListening,
      wakeWordConfidence: wakeWordConfidence ?? this.wakeWordConfidence,
    );
  }
}
