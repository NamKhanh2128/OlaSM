package com.olasm.mobile.wakeword

import android.content.Context
import ai.onnxruntime.*
import java.nio.FloatBuffer
import java.util.concurrent.atomic.AtomicBoolean

class OnnxWakeEngine(private val context: Context) {
    private var ortEnvironment: OrtEnvironment = OrtEnvironment.getEnvironment()
    private var session: OrtSession? = null
    private val isInitialized = AtomicBoolean(false)

    // 16-frame circular window for embeddings (16 x 96 features = 1536 floats)
    private val embeddingWindow = Array(16) { FloatArray(96) }
    private var windowIndex = 0

    fun initialize(modelAssetPath: String): Boolean {
        return try {
            val modelBytes = context.assets.open(modelAssetPath).readBytes()
            val sessionOptions = OrtSession.SessionOptions().apply {
                addNnapi() // Hardware accelerated execution on Android NPU/DSP
                setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
                setIntraOpNumThreads(2)
            }
            session = ortEnvironment.createSession(modelBytes, sessionOptions)
            isInitialized.set(true)
            true
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    @Synchronized
    fun processFrame(embeddingFrame: FloatArray): Float {
        if (!isInitialized.get() || session == null) return 0.0f

        embeddingWindow[windowIndex] = embeddingFrame
        windowIndex = (windowIndex + 1) % 16

        val flattened = FloatArray(1 * 16 * 96)
        for (i in 0 until 16) {
            val srcIdx = (windowIndex + i) % 16
            System.arraycopy(embeddingWindow[srcIdx], 0, flattened, i * 96, 96)
        }

        val shape = longArrayOf(1, 16, 96)
        val tensor = OnnxTensor.createTensor(ortEnvironment, FloatBuffer.wrap(flattened), shape)

        return tensor.use { t ->
            val output = session!!.run(mapOf("input" to t))
            output.use { res ->
                val rawOutput = (res[0].value as Array<FloatArray>)[0][0]
                // Sigmoid probability score
                (1.0f / (1.0f + Math.exp(-rawOutput.toDouble()).toFloat()))
            }
        }
    }

    fun release() {
        isInitialized.set(false)
        session?.close()
        session = null
    }
}
