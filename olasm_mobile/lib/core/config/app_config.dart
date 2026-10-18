/// Global application configurations and environment settings.
class AppConfig {
  static const String appName = 'OlaSM Voice Assistant';
  
  // Default backend URL (FastAPI backend)
  // For Android emulator: 10.0.2.2:8000, for iOS simulator: 127.0.0.1:8000, or LAN IP
  static const String defaultBackendUrl = 'http://10.0.2.2:8000';
  
  // LiveKit server fallback URL if not returned by backend
  static const String livekitDefaultUrl = 'ws://10.0.2.2:7880';
  
  // Audio configuration
  static const int sampleRate = 16000;
  static const int audioChannels = 1; // Mono
  static const int pcmBitDepth = 16;
  
  // WakeWord parameters
  static const double defaultWakeWordThreshold = 0.68;
  static const Duration wakeWordDebounce = Duration(seconds: 2);
  static const int preRollBufferDurationMs = 500;
}
