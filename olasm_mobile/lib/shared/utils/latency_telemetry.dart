/// Latency telemetry utility for measuring sub-millisecond timing
/// of each stage in the wake-word → agent-receives-audio pipeline.
class LatencyTelemetry {
  final Map<String, int> _checkpoints = {};
  int? _startTimeUs;

  /// Mark the beginning of the measurement window.
  void start() {
    _startTimeUs = DateTime.now().microsecondsSinceEpoch;
    _checkpoints.clear();
  }

  /// Record a named checkpoint relative to [start].
  void checkpoint(String name) {
    if (_startTimeUs == null) return;
    final elapsed = DateTime.now().microsecondsSinceEpoch - _startTimeUs!;
    _checkpoints[name] = elapsed;
  }

  /// Elapsed microseconds since [start].
  int get elapsedUs {
    if (_startTimeUs == null) return 0;
    return DateTime.now().microsecondsSinceEpoch - _startTimeUs!;
  }

  /// Elapsed milliseconds since [start].
  double get elapsedMs => elapsedUs / 1000.0;

  /// Full breakdown of checkpoints in microseconds.
  Map<String, int> get checkpoints => Map.unmodifiable(_checkpoints);

  /// Human-readable summary for debugging / logging.
  String summary() {
    if (_checkpoints.isEmpty) return 'No checkpoints recorded.';
    final buf = StringBuffer('Latency Breakdown:\n');
    int prev = 0;
    for (final entry in _checkpoints.entries) {
      final deltaMs = (entry.value - prev) / 1000.0;
      final totalMs = entry.value / 1000.0;
      buf.writeln(
        '  ${entry.key}: ${deltaMs.toStringAsFixed(1)}ms '
        '(total: ${totalMs.toStringAsFixed(1)}ms)',
      );
      prev = entry.value;
    }
    return buf.toString();
  }
}
