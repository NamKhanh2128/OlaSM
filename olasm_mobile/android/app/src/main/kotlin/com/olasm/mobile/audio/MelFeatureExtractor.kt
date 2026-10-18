package com.olasm.mobile.audio

import kotlin.math.*

/**
 * Mel Spectrogram Feature Extractor
 *
 * Converts raw PCM Int16 audio (16 kHz mono) into Mel filterbank energies
 * compatible with the Google Speech Embedding ONNX model input requirements.
 *
 * Parameters match openWakeWord's feature pipeline:
 *   - FFT size: 512 samples
 *   - Hop length: 160 samples (10 ms at 16 kHz)
 *   - Window size: 400 samples (25 ms)
 *   - Mel bins: 32
 *   - Frequency range: 60 – 7800 Hz
 */
class MelFeatureExtractor {
    private val fftSize = 512
    private val hopLength = 160
    private val windowSize = 400
    private val numMelBins = 32
    private val sampleRate = 16000
    private val fMin = 60.0
    private val fMax = 7800.0

    private val hannWindow: FloatArray = FloatArray(windowSize) { i ->
        (0.5 * (1.0 - cos(2.0 * PI * i / (windowSize - 1)))).toFloat()
    }

    private val melFilterbank: Array<FloatArray> by lazy { buildMelFilterbank() }

    /**
     * Extract [numMelBins] Mel energies for a single 80 ms frame of PCM audio.
     * @param pcmInt16 raw signed 16-bit samples (should contain ~1280 samples for 80 ms)
     * @return FloatArray of size [numMelBins]
     */
    fun extractMelFrame(pcmInt16: ShortArray): FloatArray {
        // Step 1 – Convert Int16 to float in [-1.0, 1.0]
        val floatSamples = FloatArray(pcmInt16.size) { i ->
            pcmInt16[i].toFloat() / 32768.0f
        }

        // Step 2 – Pre-emphasis filter
        val preEmphasized = FloatArray(floatSamples.size)
        preEmphasized[0] = floatSamples[0]
        for (i in 1 until floatSamples.size) {
            preEmphasized[i] = floatSamples[i] - 0.97f * floatSamples[i - 1]
        }

        // Step 3 – Extract one windowed FFT frame from centre of buffer
        val offset = (floatSamples.size - windowSize).coerceAtLeast(0) / 2
        val windowed = FloatArray(fftSize)
        for (i in 0 until windowSize) {
            windowed[i] = preEmphasized[offset + i] * hannWindow[i]
        }

        // Step 4 – Power spectrum via simple DFT (for production, use JNI/FFTW)
        val powerSpectrum = powerSpectrum(windowed)

        // Step 5 – Apply Mel filterbank
        val melEnergies = FloatArray(numMelBins)
        for (m in 0 until numMelBins) {
            var energy = 0.0f
            for (k in 0 until powerSpectrum.size) {
                energy += melFilterbank[m][k] * powerSpectrum[k]
            }
            // Log compression (log-Mel)
            melEnergies[m] = ln(energy.coerceAtLeast(1e-9f))
        }

        return melEnergies
    }

    private fun powerSpectrum(frame: FloatArray): FloatArray {
        val n = frame.size
        val re = frame.clone()
        val im = FloatArray(n)

        // Cooley-Tukey FFT (in-place, power-of-2)
        var length = n
        var half = length / 2
        while (half >= 1) {
            for (start in 0 until n step length) {
                for (i in 0 until half) {
                    val angle = -2.0 * PI * i / length
                    val wr = cos(angle).toFloat()
                    val wi = sin(angle).toFloat()
                    val tRe = wr * re[start + half + i] - wi * im[start + half + i]
                    val tIm = wr * im[start + half + i] + wi * re[start + half + i]
                    re[start + half + i] = re[start + i] - tRe
                    im[start + half + i] = im[start + i] - tIm
                    re[start + i] += tRe
                    im[start + i] += tIm
                }
            }
            length = half
            half /= 2
        }

        // Bit-reverse permutation
        var j = 0
        for (i in 1 until n) {
            var bit = n shr 1
            while (j and bit != 0) { j = j xor bit; bit = bit shr 1 }
            j = j xor bit
            if (i < j) { re[i] = re[j].also { re[j] = re[i] }; im[i] = im[j].also { im[j] = im[i] } }
        }

        val numBins = n / 2 + 1
        return FloatArray(numBins) { k -> re[k] * re[k] + im[k] * im[k] }
    }

    private fun buildMelFilterbank(): Array<FloatArray> {
        val numBins = fftSize / 2 + 1
        val melMin = hzToMel(fMin)
        val melMax = hzToMel(fMax)

        val melPoints = DoubleArray(numMelBins + 2) { i ->
            melToHz(melMin + (melMax - melMin) * i / (numMelBins + 1))
        }

        val fftFreqs = DoubleArray(numBins) { k -> k.toDouble() * sampleRate / fftSize }

        return Array(numMelBins) { m ->
            FloatArray(numBins) { k ->
                val freq = fftFreqs[k]
                val lower = melPoints[m]
                val center = melPoints[m + 1]
                val upper = melPoints[m + 2]
                when {
                    freq < lower || freq > upper -> 0.0f
                    freq < center -> ((freq - lower) / (center - lower)).toFloat()
                    else -> ((upper - freq) / (upper - center)).toFloat()
                }
            }
        }
    }

    private fun hzToMel(hz: Double) = 2595.0 * log10(1.0 + hz / 700.0)
    private fun melToHz(mel: Double) = 700.0 * (10.0.pow(mel / 2595.0) - 1.0)
}
