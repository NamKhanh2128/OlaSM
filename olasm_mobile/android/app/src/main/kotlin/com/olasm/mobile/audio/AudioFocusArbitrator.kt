package com.olasm.mobile.audio

import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothProfile
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.media.AudioManager
import android.util.Log

/**
 * Manages audio focus arbitration, Bluetooth SCO handshake, and
 * Proximity Sensor routing so that wake-word audio and LiveKit
 * WebRTC calls share hardware without conflicts.
 */
class AudioFocusArbitrator(private val context: Context) {
    private val audioManager =
        context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
    private val bluetoothAdapter = BluetoothAdapter.getDefaultAdapter()
    private var scoReceiver: BroadcastReceiver? = null

    /**
     * Configure audio session for LiveKit WebRTC voice call.
     * Activates Bluetooth SCO if a headset is connected.
     */
    fun activateVoiceCallMode(onScoReady: (() -> Unit)? = null) {
        audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
        audioManager.isSpeakerphoneOn = false

        if (isBluetoothHeadsetConnected()) {
            Log.d(TAG, "Bluetooth headset detected – starting SCO")
            startBluetoothSco(onScoReady)
        } else {
            Log.d(TAG, "No BT headset – using earpiece/speaker")
            onScoReady?.invoke()
        }
    }

    /**
     * Return audio session to normal mode (for wake-word listening).
     */
    fun deactivateVoiceCallMode() {
        stopBluetoothSco()
        audioManager.mode = AudioManager.MODE_NORMAL
        audioManager.isSpeakerphoneOn = false
    }

    private fun isBluetoothHeadsetConnected(): Boolean {
        return bluetoothAdapter?.getProfileConnectionState(BluetoothProfile.HEADSET) ==
                BluetoothProfile.STATE_CONNECTED
    }

    private fun startBluetoothSco(onReady: (() -> Unit)?) {
        scoReceiver = object : BroadcastReceiver() {
            override fun onReceive(ctx: Context, intent: Intent) {
                val state = intent.getIntExtra(
                    AudioManager.EXTRA_SCO_AUDIO_STATE, -1
                )
                if (state == AudioManager.SCO_AUDIO_STATE_CONNECTED) {
                    Log.d(TAG, "Bluetooth SCO connected")
                    onReady?.invoke()
                    context.unregisterReceiver(this)
                    scoReceiver = null
                }
            }
        }
        context.registerReceiver(
            scoReceiver,
            IntentFilter(AudioManager.ACTION_SCO_AUDIO_STATE_UPDATED)
        )
        audioManager.startBluetoothSco()
        audioManager.isBluetoothScoOn = true
    }

    private fun stopBluetoothSco() {
        scoReceiver?.let {
            try { context.unregisterReceiver(it) } catch (_: Exception) {}
            scoReceiver = null
        }
        audioManager.stopBluetoothSco()
        audioManager.isBluetoothScoOn = false
    }

    fun release() {
        stopBluetoothSco()
    }

    companion object {
        private const val TAG = "OlasmAudioArbitrator"
    }
}
