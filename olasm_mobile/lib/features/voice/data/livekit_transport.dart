import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:livekit_client/livekit_client.dart';
import '../../../../core/network/token_cache_manager.dart';
import '../domain/models/booking_state.dart';

typedef AudioLevelCallback = void Function(double level);
typedef TranscriptCallback = void Function(String text, bool isFinal, bool isAgent);
typedef BookingUpdateCallback = void Function(BookingState booking);
typedef StatusChangeCallback = void Function(RoomStatus status);

/// LiveKitTransport: Manages WebRTC connection, audio tracks, and real-time state sync.
class LiveKitTransport {
  Room? _room;
  EventsListener<RoomEvent>? _listener;

  AudioLevelCallback? onAudioLevel;
  TranscriptCallback? onTranscript;
  BookingUpdateCallback? onBookingUpdate;
  StatusChangeCallback? onStatusChange;
  VoidCallback? onDisconnected;

  Room? get room => _room;
  bool get isConnected => _room?.connectionState == ConnectionState.connected;

  /// Connect to LiveKit room with credentials
  Future<void> connect(MobileVoiceCredentials credentials) async {
    await disconnect();

    _room = Room(
      roomOptions: const RoomOptions(
        adaptiveStream: true,
        dynacast: true,
        defaultAudioPublishOptions: AudioPublishOptions(
          dtx: true,
          stopMicOnMute: false,
        ),
      ),
    );

    _listener = _room!.createListener();
    _setupEventListeners(_listener!);

    await _room!.connect(
      credentials.serverUrl,
      credentials.participantToken,
      fastConnectOptions: FastConnectOptions(
        microphone: const TrackOption(enabled: true),
      ),
    );

    // Publish local microphone track
    await _room!.localParticipant?.setMicrophoneEnabled(true);
  }

  void _setupEventListeners(EventsListener<RoomEvent> listener) {
    listener
      ..on<DataReceivedEvent>((event) {
        _handleDataReceived(event);
      })
      ..on<TrackSubscribedEvent>((event) {
        if (event.track is AudioTrack) {
          debugPrint('Subscribed to Agent AudioTrack');
        }
      })
      ..on<TranscriptionEvent>((event) {
        for (final seg in event.transcription.segments) {
          final isAgent = event.participant?.identity != _room?.localParticipant?.identity;
          onTranscript?.call(seg.text, seg.isFinal, isAgent);
        }
      })
      ..on<RoomDisconnectedEvent>((event) {
        onDisconnected?.call();
      });
  }

  void _handleDataReceived(DataReceivedEvent event) {
    try {
      final text = utf8.decode(event.data);
      final json = jsonDecode(text) as Map<String, dynamic>;

      // Check if this is a state sync packet or booking packet
      final isBookingTopic = event.topic == 'olasm.booking_state.v1' || event.topic == 'alosm.booking_state.v1';
      final hasBookingKeys = json.containsKey('booking') ||
          json.containsKey('booking_id') ||
          json.containsKey('pickup_location') ||
          json.containsKey('pickup') ||
          json.containsKey('destination') ||
          json.containsKey('quote');

      if (isBookingTopic || hasBookingKeys) {
        final bookingData = (json.containsKey('booking') && json['booking'] is Map<String, dynamic>)
            ? (json['booking'] as Map<String, dynamic>)
            : json;
        final updatedBooking = BookingState.fromDataChannel(bookingData);
        onBookingUpdate?.call(updatedBooking);
      }

      // Check for transcript events
      if (json.containsKey('transcript')) {
        final transcriptText = json['transcript'] as String;
        final isAgent = json['role'] == 'agent' || json['is_agent'] == true;
        final isFinal = json['is_final'] as bool? ?? true;
        onTranscript?.call(transcriptText, isFinal, isAgent);
      }
    } catch (e) {
      debugPrint('Error parsing data channel message: $e');
    }
  }

  /// Push buffered PCM frames captured during pre-connect phase
  Future<void> flushPreConnectBuffer(List<Uint8List> frames) async {
    if (_room == null || !isConnected) return;
    for (final frame in frames) {
      await _room!.localParticipant?.publishData(
        frame,
        topic: 'lk.agent.pre-connect-audio-buffer',
      );
    }
  }

  Future<void> disconnect() async {
    _listener?.dispose();
    _listener = null;
    await _room?.disconnect();
    await _room?.dispose();
    _room = null;
  }
}
