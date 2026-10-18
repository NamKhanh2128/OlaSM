import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/theme/app_theme.dart';
import 'features/voice/presentation/screens/voice_interaction_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Enforce portrait-only mode for voice assistant UX
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  // Full dark immersive UI
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.light,
      systemNavigationBarColor: kColorBackground,
      systemNavigationBarIconBrightness: Brightness.light,
    ),
  );

  runApp(
    // ProviderScope wraps entire app for Riverpod state management
    const ProviderScope(
      child: OlasmApp(),
    ),
  );
}

class OlasmApp extends StatelessWidget {
  const OlasmApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'OlaSM Voice',
      debugShowCheckedModeBanner: false,
      themeMode: ThemeMode.dark,
      darkTheme: buildOlasmTheme(),
      home: const VoiceInteractionScreen(),
    );
  }
}
