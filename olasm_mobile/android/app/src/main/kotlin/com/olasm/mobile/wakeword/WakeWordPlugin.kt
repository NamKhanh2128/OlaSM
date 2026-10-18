package com.olasm.mobile.wakeword

import android.content.Context
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Handler
import android.os.Looper
import com.olasm.mobile.audio.MelFeatureExtractor
import com.olasm.mobile.audio.AudioFocusArbitrator
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import java.util.ArrayDeque
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.concurrent.thread

/**
 * Flutter plugin that bridges Dart ↔ Native Android for wake word detection.
 *
 * Architecture:
 *  - AudioRecord captures 16 kHz mono PCM into 80 ms frames
 *  - MelFeatureExtractor computes Mel spectrogram features
 *  - OnnxWakeEngine runs Conv-Attention classifier (NNAPI acceleration)
 *  - EventChannel fires detection events to Dart when score > threshold
 *  - MethodChannel exposes initialize / startListening / pauseListening /
 *    resumeListening / getPreRollBuffer / dispose
 */
class WakeWordPlugin : FlutterPlugin, MethodChannel.MethodCallHandler,
    EventChannel.StreamHandler {

    private lateinit var context: Context
    private lateinit var methodChannel: MethodChannel
    private lateinit var eventChannel: EventChannel
    private var eventSink: EventChannel.EventSink? = null

    private var onnxEngine: OnnxWakeEngine? = null
    private val melExtractor = MelFeatureExtractor()
    private val mainHandler = Handler(Looper.getMainLooper())
    private val isListening = AtomicBoolean(false)
    private var audioRecord: AudioRecord? = null
    private var audioThread: Thread? = null

    private var threshold: Float = 0.68f
    private var lastTriggerMs: Long = 0L
    private val debounceMs: Long = 2000L // 2-second debounce

    // 500 ms pre-roll buffer: 6 frames × 80 ms = 480 ms ≈ 500 ms
    private val preRollBuffer = ArrayDeque<ByteArray>(8)
    private val maxPreRollFrames = 6

    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        context = binding.applicationContext
        onnxEngine = OnnxWakeEngine(context)

        methodChannel = MethodChannel(
            binding.binaryMessenger, "com.olasm.mobile/wakeword"
        )
        methodChannel.setMethodCallHandler(this)

        eventChannel = EventChannel(
            binding.binaryMessenger, "com.olasm.mobile/wakeword_events"
        )
        eventChannel.setStreamHandler(this)
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "initialize" -> {
                val modelPath = call.argument<String>("modelPath")
                    ?: "hey_olasm_int8.onnx"
                threshold = (call.argument<Double>("threshold") ?: 0.68).toFloat()
                val ok = onnxEngine?.initialize(modelPath) ?: false
                result.success(ok)
            }

            "startListening" -> {
                WakeWordService.start(context)
                startAudioCapture()
                result.success(true)
            }

            "pauseListening" -> {
                isListening.set(false)
                WakeWordService.stop(context)
                result.success(true)
            }

            "resumeListening" -> {
                WakeWordService.start(context)
                startAudioCapture()
                result.success(true)
            }

            "getPreRollBuffer" -> {
                synchronized(preRollBuffer) {
                    result.success(preRollBuffer.toList())
                }
            }

            "dispose" -> {
                isListening.set(false)
                WakeWordService.stop(context)
                audioRecord?.stop()
                audioRecord?.release()
                audioRecord = null
                onnxEngine?.release()
                result.success(true)
            }

            else -> result.notImplemented()
        }
    }

    private fun startAudioCapture() {
        if (isListening.getAndSet(true)) return // already running

        audioThread = thread(
            name = "olasm-wakeword",
            priority = Thread.MAX_PRIORITY - 1,
        ) {
            val sampleRate = 16_000
            val frameSize = 1280         // 80 ms @ 16 kHz
            val minBuf = AudioRecord.getMinBufferSize(
                sampleRate,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT
            )

            val record = AudioRecord(
                MediaRecorder.AudioSource.VOICE_RECOGNITION,
                sampleRate,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                minBuf.coerceAtLeast(frameSize * 2)
            )
            audioRecord = record
            record.startRecording()

            val shortBuf = ShortArray(frameSize)
            val byteBuf = ByteArray(frameSize * 2)

            while (isListening.get()) {
                val read = record.read(shortBuf, 0, frameSize)
                if (read <= 0) continue

                // Store raw bytes for pre-roll buffer
                for (i in 0 until read) {
                    byteBuf[i * 2] = (shortBuf[i].toInt() and 0xFF).toByte()
                    byteBuf[i * 2 + 1] = ((shortBuf[i].toInt() shr 8) and 0xFF).toByte()
                }
                synchronized(preRollBuffer) {
                    preRollBuffer.addLast(byteBuf.clone())
                    while (preRollBuffer.size > maxPreRollFrames) {
                        preRollBuffer.removeFirst()
                    }
                }

                // Feature extraction → inference
                val melFeatures = melExtractor.extractMelFrame(shortBuf)
                val score = onnxEngine?.processFrame(melFeatures) ?: 0.0f

                // Trigger with debounce
                val now = System.currentTimeMillis()
                if (score > threshold && now - lastTriggerMs > debounceMs) {
                    lastTriggerMs = now
                    mainHandler.post {
                        eventSink?.success(
                            mapOf(
                                "keyword" to "hey_olasm",
                                "score" to score,
                                "timestamp" to now
                            )
                        )
                    }
                }
            }

            record.stop()
            record.release()
            audioRecord = null
        }
    }

    // ── EventChannel.StreamHandler ─────────────────────────────────────
    override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
        eventSink = events
    }

    override fun onCancel(arguments: Any?) {
        eventSink = null
    }

    // ── FlutterPlugin ──────────────────────────────────────────────────
    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        isListening.set(false)
        methodChannel.setMethodCallHandler(null)
        eventChannel.setStreamHandler(null)
    }
}
