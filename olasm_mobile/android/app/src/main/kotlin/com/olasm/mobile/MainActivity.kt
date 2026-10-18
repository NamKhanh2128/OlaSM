package com.olasm.mobile

import com.olasm.mobile.wakeword.WakeWordPlugin
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        // Register the WakeWord native plugin
        flutterEngine.plugins.add(WakeWordPlugin())
    }
}
