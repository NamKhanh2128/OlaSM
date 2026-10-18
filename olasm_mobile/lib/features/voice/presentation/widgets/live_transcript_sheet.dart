import 'package:flutter/material.dart';

/// Live transcript overlay showing real-time user speech and agent response.
class LiveTranscriptSheet extends StatelessWidget {
  final String? userTranscript;
  final String? agentResponse;
  final bool isVisible;

  const LiveTranscriptSheet({
    super.key,
    this.userTranscript,
    this.agentResponse,
    this.isVisible = false,
  });

  @override
  Widget build(BuildContext context) {
    if (!isVisible || (userTranscript == null && agentResponse == null)) {
      return const SizedBox.shrink();
    }

    return AnimatedOpacity(
      opacity: isVisible ? 1.0 : 0.0,
      duration: const Duration(milliseconds: 300),
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 20),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.black.withOpacity(0.65),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white12),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.3),
              blurRadius: 20,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            // Agent utterance
            if (agentResponse != null && agentResponse!.isNotEmpty)
              _buildBubble(
                text: agentResponse!,
                isAgent: true,
              ),

            if (userTranscript != null &&
                userTranscript!.isNotEmpty &&
                agentResponse != null)
              const SizedBox(height: 8),

            // User transcript (streaming)
            if (userTranscript != null && userTranscript!.isNotEmpty)
              _buildBubble(
                text: userTranscript!,
                isAgent: false,
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildBubble({required String text, required bool isAgent}) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 28,
          height: 28,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: isAgent
                ? const Color(0xFF00E676).withOpacity(0.2)
                : const Color(0xFF00B0FF).withOpacity(0.2),
          ),
          child: Icon(
            isAgent ? Icons.smart_toy_rounded : Icons.person_rounded,
            size: 16,
            color: isAgent
                ? const Color(0xFF00E676)
                : const Color(0xFF00B0FF),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                isAgent ? 'OlaSM Agent' : 'Bạn',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: isAgent
                      ? const Color(0xFF00E676)
                      : const Color(0xFF00B0FF),
                ),
              ),
              const SizedBox(height: 3),
              Text(
                text,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 14,
                  height: 1.4,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
