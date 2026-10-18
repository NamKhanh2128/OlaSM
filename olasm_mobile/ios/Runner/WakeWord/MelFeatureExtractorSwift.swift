import Foundation
import Accelerate

/**
 * MelFeatureExtractorSwift
 *
 * Converts raw PCM Int16 audio (16 kHz mono) to log-Mel spectrogram features
 * using Apple's Accelerate framework (vDSP) for efficient SIMD computation.
 *
 * Output: [numMelBins] Float32 values per 80ms frame — same shape as the
 * Google Speech Embedding ONNX model input.
 */
@objc public class MelFeatureExtractorSwift: NSObject {
    private let fftSize: Int = 512
    private let windowSize: Int = 400
    private let numMelBins: Int = 32
    private let sampleRate: Double = 16_000
    private let fMin: Double = 60.0
    private let fMax: Double = 7800.0

    private let hannWindow: [Float]
    private let melFilterbank: [[Float]]
    private var fftSetup: FFTSetup

    override public init() {
        // Pre-compute Hann window
        var hann = [Float](repeating: 0, count: windowSize)
        vDSP_hann_window(&hann, vDSP_Length(windowSize), Int32(vDSP_HANN_NORM))
        hannWindow = hann

        // FFT setup
        let log2n = vDSP_Length(log2(Double(fftSize)))
        fftSetup = vDSP_create_fftsetup(log2n, FFTRadix(FFT_RADIX2))!

        // Build Mel filterbank
        func hzToMel(_ hz: Double) -> Double {
            2595.0 * log10(1.0 + hz / 700.0)
        }
        func melToHz(_ mel: Double) -> Double {
            700.0 * (pow(10.0, mel / 2595.0) - 1.0)
        }

        let melMin = hzToMel(60.0)
        let melMax = hzToMel(7800.0)
        let numBins = fftSize / 2 + 1

        var melPoints = [Double](repeating: 0, count: 34) // numMelBins+2
        for i in 0..<34 {
            let mel = melMin + (melMax - melMin) * Double(i) / 33.0
            melPoints[i] = melToHz(mel)
        }

        var filterbank = [[Float]]()
        for m in 0..<32 {
            var filter = [Float](repeating: 0, count: numBins)
            for k in 0..<numBins {
                let freq = Double(k) * 16000.0 / Double(fftSize)
                let lo = melPoints[m]
                let center = melPoints[m + 1]
                let hi = melPoints[m + 2]
                if freq >= lo && freq < center {
                    filter[k] = Float((freq - lo) / (center - lo))
                } else if freq >= center && freq <= hi {
                    filter[k] = Float((hi - freq) / (hi - center))
                }
            }
            filterbank.append(filter)
        }
        melFilterbank = filterbank

        super.init()
    }

    deinit {
        vDSP_destroy_fftsetup(fftSetup)
    }

    /**
     * Extract log-Mel features from a 80 ms PCM Int16 frame.
     * - Parameter pcmData: Raw Data containing Int16 samples at 16 kHz.
     * - Returns: [Float] of length numMelBins (32).
     */
    @objc public func extractMelFrame(pcmData: Data) -> [Float] {
        let count = pcmData.count / MemoryLayout<Int16>.size
        var floatSamples = [Float](repeating: 0, count: count)

        pcmData.withUnsafeBytes { ptr in
            guard let int16Ptr = ptr.baseAddress?.assumingMemoryBound(to: Int16.self) else { return }
            vDSP_vflt16(int16Ptr, 1, &floatSamples, 1, vDSP_Length(count))
        }
        // Normalise to [-1, 1]
        var scale: Float = 1.0 / 32768.0
        vDSP_vsmul(floatSamples, 1, &scale, &floatSamples, 1, vDSP_Length(count))

        // Pre-emphasis
        var preEmph = floatSamples
        var alpha: Float = -0.97
        vDSP_vsmsa(
            Array(floatSamples.dropFirst()), 1,
            &alpha,
            Array(floatSamples.dropLast()), 1,
            &preEmph, 1,
            vDSP_Length(count - 1)
        )

        // Window and zero-pad to fftSize
        var windowed = [Float](repeating: 0, count: fftSize)
        let offset = max(0, (count - windowSize) / 2)
        for i in 0..<min(windowSize, count - offset) {
            windowed[i] = preEmph[offset + i] * hannWindow[i]
        }

        // FFT using vDSP
        var real = windowed
        var imag = [Float](repeating: 0, count: fftSize)
        var splitComplex = DSPSplitComplex(realp: &real, imagp: &imag)

        let log2n = vDSP_Length(log2(Float(fftSize)))
        vDSP_fft_zip(fftSetup, &splitComplex, 1, log2n, FFTDirection(FFT_FORWARD))

        let numBins = fftSize / 2 + 1
        var powerSpectrum = [Float](repeating: 0, count: numBins)
        vDSP_zvmags(&splitComplex, 1, &powerSpectrum, 1, vDSP_Length(numBins))

        // Mel filterbank + log compression
        var melEnergies = [Float](repeating: 0, count: numMelBins)
        for m in 0..<numMelBins {
            var dot: Float = 0
            vDSP_dotpr(melFilterbank[m], 1, powerSpectrum, 1, &dot, vDSP_Length(numBins))
            melEnergies[m] = log(max(dot, 1e-9))
        }

        return melEnergies
    }
}
