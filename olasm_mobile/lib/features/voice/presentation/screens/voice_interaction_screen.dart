import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../domain/controllers/voice_session_controller.dart';
import '../../domain/models/voice_session_state.dart';
import '../widgets/booking_card_widget.dart';
import '../widgets/booking_map_widget.dart';
import '../widgets/dynamic_orb_visualizer.dart';
import '../widgets/live_transcript_sheet.dart';
import '../widgets/wakeword_pill_indicator.dart';
import '../widgets/audio_waveform_widget.dart';

class VoiceInteractionScreen extends ConsumerStatefulWidget {
  const VoiceInteractionScreen({super.key});

  @override
  ConsumerState<VoiceInteractionScreen> createState() =>
      _VoiceInteractionScreenState();
}

class _VoiceInteractionScreenState
    extends ConsumerState<VoiceInteractionScreen>
    with TickerProviderStateMixin {
  late AnimationController _bgController;
  late Animation<double> _bgAnimation;

  @override
  void initState() {
    super.initState();
    _bgController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 8),
    )..repeat(reverse: true);

    _bgAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _bgController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _bgController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(voiceSessionProvider);
    final controller = ref.read(voiceSessionProvider.notifier);

    return Scaffold(
      backgroundColor: const Color(0xFF0A0D14),
      body: Stack(
        fit: StackFit.expand,
        children: [
          // ── Animated ambient background ─────────────────────────
          AnimatedBuilder(
            animation: _bgAnimation,
            builder: (_, __) => Stack(
              children: [
                Positioned(
                  top: -120 + _bgAnimation.value * 30,
                  left: -80 + _bgAnimation.value * 20,
                  child: _AmbientBlob(
                    size: 320,
                    color: const Color(0xFF00E676),
                    opacity: state.isActive ? 0.15 : 0.08,
                  ),
                ),
                Positioned(
                  bottom: 60 - _bgAnimation.value * 20,
                  right: -60 + _bgAnimation.value * 15,
                  child: _AmbientBlob(
                    size: 280,
                    color: const Color(0xFF00B0FF),
                    opacity: state.isActive ? 0.12 : 0.06,
                  ),
                ),
                if (state.status == VoiceSessionStatus.agentSpeaking)
                  Positioned(
                    top: MediaQuery.of(context).size.height * 0.35,
                    right: -40,
                    child: _AmbientBlob(
                      size: 200,
                      color: const Color(0xFF7C4DFF),
                      opacity: 0.12,
                    ),
                  ),
              ],
            ),
          ),

          // ── Main content ─────────────────────────────────────────
          SafeArea(
            child: Column(
              children: [
                // Top bar
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 12, 16, 0),
                  child: Row(
                    children: [
                      // App logo / title
                      Text(
                        'OlaSM',
                        style: GoogleFonts.inter(
                          fontSize: 22,
                          fontWeight: FontWeight.w800,
                          color: Colors.white,
                          letterSpacing: -0.5,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        'Voice',
                        style: GoogleFonts.inter(
                          fontSize: 22,
                          fontWeight: FontWeight.w300,
                          color: const Color(0xFF00E676),
                          letterSpacing: -0.5,
                        ),
                      ),
                      const Spacer(),
                      // Settings button
                      IconButton(
                        icon: const Icon(
                          Icons.tune_rounded,
                          color: Colors.white54,
                          size: 22,
                        ),
                        onPressed: () => _showSettingsSheet(context),
                      ),
                    ],
                  ),
                ),

                // Wake word pill
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 10, 20, 0),
                  child: Row(
                    children: [
                      WakeWordPillIndicator(
                        isListening:
                            state.isWakeWordListening && !state.isActive,
                        confidence: state.wakeWordConfidence,
                      ),
                    ],
                  ),
                ),

                // Booking route map & card (real-time data from agent)
                if (state.booking.pickupLocation != null) ...[
                  Padding(
                    padding: const EdgeInsets.only(top: 10),
                    child: BookingMapWidget(booking: state.booking, height: 170),
                  ),
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: BookingCardWidget(booking: state.booking),
                  ),
                ],

                const Spacer(),

                // ── Center orb ───────────────────────────────────
                GestureDetector(
                  onTap: () {
                    if (state.isActive) {
                      HapticFeedback.lightImpact();
                      controller.endVoiceSession();
                    } else if (state.status !=
                        VoiceSessionStatus.connecting) {
                      HapticFeedback.mediumImpact();
                      controller.startVoiceSession(
                          triggerSource: 'push_to_talk');
                    }
                  },
                  child: DynamicOrbVisualizer(
                    audioLevel: state.audioLevel,
                    isActive: state.isActive,
                    isAgentSpeaking:
                        state.status == VoiceSessionStatus.agentSpeaking,
                  ),
                ),

                const SizedBox(height: 16),

                // Waveform bar (only when active)
                AnimatedOpacity(
                  opacity: state.isActive ? 1.0 : 0.0,
                  duration: const Duration(milliseconds: 400),
                  child: AudioWaveformWidget(
                    audioLevel: state.audioLevel,
                    color: state.status == VoiceSessionStatus.agentSpeaking
                        ? const Color(0xFF00E676)
                        : const Color(0xFF00B0FF),
                    width: MediaQuery.of(context).size.width * 0.7,
                    height: 36,
                  ),
                ),

                const SizedBox(height: 24),

                // Status text
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 32),
                  child: _buildStatusLabel(state),
                ),

                const SizedBox(height: 20),

                // Live transcript sheet
                LiveTranscriptSheet(
                  userTranscript: state.currentTranscript,
                  agentResponse: state.lastAgentUtterance,
                  isVisible: state.isActive || state.lastAgentUtterance != null,
                ),

                const Spacer(),

                // ── Bottom action bar ─────────────────────────────
                _buildBottomBar(context, state, controller),
              ],
            ),
          ),

          // Error overlay
          if (state.status == VoiceSessionStatus.error)
            _ErrorBanner(message: state.errorMessage),
        ],
      ),
    );
  }

  Widget _buildStatusLabel(VoiceSessionState state) {
    String text;
    Color color;

    switch (state.status) {
      case VoiceSessionStatus.idle:
        text = "Nói 'Hey OlaSM' hoặc chạm biểu tượng để bắt đầu";
        color = Colors.white38;
        break;
      case VoiceSessionStatus.connecting:
        text = "Đang kết nối tổng đài viên AI…";
        color = const Color(0xFF00B0FF);
        break;
      case VoiceSessionStatus.connected:
        text = "Đang nghe bạn…";
        color = Colors.white70;
        break;
      case VoiceSessionStatus.userSpeaking:
        text = "Đang nhận giọng nói…";
        color = const Color(0xFF00B0FF);
        break;
      case VoiceSessionStatus.agentSpeaking:
        text = "Tổng đài viên đang trả lời…";
        color = const Color(0xFF00E676);
        break;
      case VoiceSessionStatus.disconnecting:
        text = "Đang kết thúc phiên…";
        color = Colors.white38;
        break;
      case VoiceSessionStatus.error:
        text = state.errorMessage ?? "Đã xảy ra lỗi";
        color = const Color(0xFFFF5252);
        break;
    }

    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 300),
      child: Text(
        text,
        key: ValueKey(state.status),
        textAlign: TextAlign.center,
        style: GoogleFonts.inter(
          fontSize: 14,
          color: color,
          height: 1.5,
        ),
      ),
    );
  }

  Widget _buildBottomBar(
    BuildContext context,
    VoiceSessionState state,
    VoiceSessionController controller,
  ) {
    return Padding(
      padding: EdgeInsets.only(
        left: 24,
        right: 24,
        bottom: MediaQuery.of(context).padding.bottom + 16,
      ),
      child: state.isActive || state.status == VoiceSessionStatus.connecting
          ? Row(
              children: [
                // Mute button (placeholder)
                _CircleIconButton(
                  icon: Icons.mic_off_rounded,
                  color: Colors.white24,
                  onTap: () {},
                ),
                const SizedBox(width: 16),
                // End call – full width
                Expanded(
                  child: _ActionButton(
                    label: 'Kết thúc cuộc gọi',
                    icon: Icons.call_end_rounded,
                    backgroundColor: const Color(0xFFFF3D00),
                    onPressed: () {
                      HapticFeedback.heavyImpact();
                      controller.endVoiceSession();
                    },
                  ),
                ),
                const SizedBox(width: 16),
                // Speaker button (placeholder)
                _CircleIconButton(
                  icon: Icons.volume_up_rounded,
                  color: Colors.white24,
                  onTap: () {},
                ),
              ],
            )
          : _ActionButton(
              label: "Nhấn để gọi (Push to Talk)",
              icon: Icons.mic_rounded,
              backgroundColor: const Color(0xFF00E676),
              foregroundColor: Colors.black87,
              onPressed: () {
                HapticFeedback.mediumImpact();
                controller.startVoiceSession(triggerSource: 'push_to_talk');
              },
            ),
    );
  }

  void _showSettingsSheet(BuildContext context) {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF1A1E2A),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => const _SettingsSheet(),
    );
  }
}

// ── Supporting widgets ─────────────────────────────────────────────────

class _AmbientBlob extends StatelessWidget {
  final double size;
  final Color color;
  final double opacity;

  const _AmbientBlob({
    required this.size,
    required this.color,
    required this.opacity,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: color.withOpacity(opacity),
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final Color backgroundColor;
  final Color foregroundColor;
  final VoidCallback onPressed;

  const _ActionButton({
    required this.label,
    required this.icon,
    required this.backgroundColor,
    this.foregroundColor = Colors.white,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: backgroundColor,
      borderRadius: BorderRadius.circular(18),
      child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(18),
        child: Container(
          height: 56,
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, color: foregroundColor, size: 22),
              const SizedBox(width: 10),
              Text(
                label,
                style: GoogleFonts.inter(
                  color: foregroundColor,
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CircleIconButton extends StatelessWidget {
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  const _CircleIconButton({
    required this.icon,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 48,
        height: 48,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: color,
        ),
        child: Icon(icon, color: Colors.white70, size: 22),
      ),
    );
  }
}

class _ErrorBanner extends StatelessWidget {
  final String? message;

  const _ErrorBanner({this.message});

  @override
  Widget build(BuildContext context) {
    return Positioned(
      top: 0,
      left: 0,
      right: 0,
      child: Material(
        color: const Color(0xFFFF3D00),
        child: SafeArea(
          bottom: false,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Row(
              children: [
                const Icon(Icons.error_outline_rounded,
                    color: Colors.white, size: 20),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    message ?? 'Lỗi kết nối',
                    style: const TextStyle(color: Colors.white, fontSize: 13),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _SettingsSheet extends StatelessWidget {
  const _SettingsSheet();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Cài đặt',
            style: GoogleFonts.inter(
              color: Colors.white,
              fontSize: 20,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 20),
          _SettingsRow(
            icon: Icons.record_voice_over_rounded,
            label: 'Wake word: "Hey OlaSM"',
            trailing: const Icon(Icons.chevron_right_rounded,
                color: Colors.white38),
            onTap: () {},
          ),
          _SettingsRow(
            icon: Icons.threshold,
            label: 'Ngưỡng nhận diện: 0.68',
            trailing: const Icon(Icons.chevron_right_rounded,
                color: Colors.white38),
            onTap: () {},
          ),
          _SettingsRow(
            icon: Icons.language_rounded,
            label: 'Backend URL',
            trailing: const Icon(Icons.chevron_right_rounded,
                color: Colors.white38),
            onTap: () {},
          ),
          const SizedBox(height: 8),
        ],
      ),
    );
  }
}

class _SettingsRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final Widget trailing;
  final VoidCallback onTap;

  const _SettingsRow({
    required this.icon,
    required this.label,
    required this.trailing,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: Container(
        width: 38,
        height: 38,
        decoration: BoxDecoration(
          color: const Color(0xFF00E676).withOpacity(0.12),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Icon(icon, color: const Color(0xFF00E676), size: 18),
      ),
      title: Text(
        label,
        style: const TextStyle(color: Colors.white, fontSize: 14),
      ),
      trailing: trailing,
      onTap: onTap,
    );
  }
}
