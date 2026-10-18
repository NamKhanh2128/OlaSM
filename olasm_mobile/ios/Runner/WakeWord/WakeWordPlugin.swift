import Flutter
import UIKit
import AVFoundation

/**
 * WakeWordPlugin (iOS)
 *
 * Flutter plugin bridging Dart ↔ Swift for wake word detection on iOS.
 *
 * Pipeline:
 *  1. AVAudioEngine captures 16 kHz mono PCM via installTap
 *  2. MelFeatureExtractorSwift computes log-Mel features (vDSP Accelerate)
 *  3. CoreMLOnnxRunner feeds features into ONNX Conv-Attention model
 *  4. Detections are sent to Dart via EventChannel with debounce
 *  5. Pre-roll buffer provides 500 ms of audio captured before detection
 */
public class WakeWordPlugin: NSObject, FlutterPlugin, FlutterStreamHandler {
    private var eventSink: FlutterEventSink?

    private let runner = CoreMLOnnxRunner()
    private let melExtractor = MelFeatureExtractorSwift()
    private let audioEngine = AVAudioEngine()

    private var isListening: Bool = false
    private var threshold: Float = 0.68
    private var lastTriggerTime: TimeInterval = 0
    private let debounceSeconds: TimeInterval = 2.0

    // 500 ms pre-roll: ~6 taps of 80 ms each
    private var preRollBuffer: [Data] = []
    private let maxPreRollFrames: Int = 6
    private let preRollLock = NSLock()

    // MARK: – Registration

    public static func register(with registrar: FlutterPluginRegistrar) {
        let methodChannel = FlutterMethodChannel(
            name: "com.olasm.mobile/wakeword",
            binaryMessenger: registrar.messenger()
        )
        let eventChannel = FlutterEventChannel(
            name: "com.olasm.mobile/wakeword_events",
            binaryMessenger: registrar.messenger()
        )
        let instance = WakeWordPlugin()
        registrar.addMethodCallDelegate(instance, channel: methodChannel)
        eventChannel.setStreamHandler(instance)
    }

    // MARK: – MethodCallHandler

    public func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
        switch call.method {

        case "initialize":
            guard let args = call.arguments as? [String: Any],
                  let modelPath = args["modelPath"] as? String else {
                result(false); return
            }
            threshold = (args["threshold"] as? Double).map { Float($0) } ?? 0.68
            let ok = runner.initializeModel(modelPath: modelPath)
            result(ok)

        case "startListening":
            startListening()
            result(true)

        case "pauseListening":
            pauseListening()
            result(true)

        case "resumeListening":
            startListening()
            result(true)

        case "getPreRollBuffer":
            preRollLock.lock()
            let frames = preRollBuffer
            preRollLock.unlock()
            result(frames)

        case "dispose":
            pauseListening()
            runner.releaseModel()
            result(true)

        default:
            result(FlutterMethodNotImplemented)
        }
    }

    // MARK: – Audio Engine

    private func startListening() {
        guard !isListening else { return }
        isListening = true

        // Configure AVAudioSession for wake-word (low-latency, background audio)
        let session = AVAudioSession.sharedInstance()
        try? session.setCategory(
            .playAndRecord,
            mode: .voiceChat,
            options: [.allowBluetooth, .allowBluetoothA2DP, .defaultToSpeaker]
        )
        try? session.setPreferredSampleRate(16_000)
        try? session.setActive(true)

        let inputNode = audioEngine.inputNode
        // Request 16 kHz mono int16 — matches our feature extractor expectations
        let recordFormat = AVAudioFormat(
            commonFormat: .pcmFormatInt16,
            sampleRate: 16_000,
            channels: 1,
            interleaved: true
        )!

        inputNode.installTap(
            onBus: 0,
            bufferSize: 1280, // 80 ms @ 16 kHz
            format: recordFormat
        ) { [weak self] buffer, _ in
            guard let self = self, self.isListening else { return }

            // Capture raw bytes for pre-roll
            guard let channelData = buffer.int16ChannelData else { return }
            let frameCount = Int(buffer.frameLength)
            let rawData = Data(
                bytes: channelData[0],
                count: frameCount * MemoryLayout<Int16>.size
            )

            self.preRollLock.lock()
            self.preRollBuffer.append(rawData)
            if self.preRollBuffer.count > self.maxPreRollFrames {
                self.preRollBuffer.removeFirst()
            }
            self.preRollLock.unlock()

            // Feature extraction + inference
            let melFeatures = self.melExtractor.extractMelFrame(pcmData: rawData)
            let score = self.runner.evaluateFrame(features: melFeatures)

            // Debounced detection event
            let now = Date().timeIntervalSince1970
            if score > self.threshold && now - self.lastTriggerTime > self.debounceSeconds {
                self.lastTriggerTime = now
                DispatchQueue.main.async {
                    self.eventSink?([
                        "keyword": "hey_olasm",
                        "score": score,
                        "timestamp": Int(now * 1000)
                    ])
                }
            }
        }

        do {
            try audioEngine.start()
        } catch {
            isListening = false
            print("[WakeWordPlugin] Failed to start audio engine: \(error)")
        }
    }

    private func pauseListening() {
        guard isListening else { return }
        isListening = false
        audioEngine.inputNode.removeTap(onBus: 0)
        audioEngine.stop()

        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }

    // MARK: – FlutterStreamHandler

    public func onListen(
        withArguments arguments: Any?,
        eventSink events: @escaping FlutterEventSink
    ) -> FlutterError? {
        self.eventSink = events
        return nil
    }

    public func onCancel(withArguments arguments: Any?) -> FlutterError? {
        self.eventSink = nil
        return nil
    }
}
