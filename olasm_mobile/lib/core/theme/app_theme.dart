import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// OlaSM design system: colours, text styles, gradients, and theme data.

// ── Color palette ──────────────────────────────────────────────────────
const kColorBackground = Color(0xFF0A0D14);
const kColorSurface = Color(0xFF1A1E2A);
const kColorSurface2 = Color(0xFF242838);

const kColorPrimary = Color(0xFF00E676);     // Emerald green (agent)
const kColorSecondary = Color(0xFF00B0FF);   // Electric blue (user)
const kColorAccent = Color(0xFF7C4DFF);      // Deep violet
const kColorError = Color(0xFFFF3D00);       // Alert red/orange

const kColorTextPrimary = Colors.white;
const kColorTextSecondary = Color(0xFFB0B8C8);
const kColorTextMuted = Color(0xFF6B7280);

// ── Typography ─────────────────────────────────────────────────────────
TextStyle kHeadlineLarge() => GoogleFonts.inter(
      fontSize: 28,
      fontWeight: FontWeight.w800,
      color: kColorTextPrimary,
      letterSpacing: -0.8,
    );

TextStyle kTitleMedium() => GoogleFonts.inter(
      fontSize: 16,
      fontWeight: FontWeight.w600,
      color: kColorTextPrimary,
    );

TextStyle kBodyMedium() => GoogleFonts.inter(
      fontSize: 14,
      fontWeight: FontWeight.w400,
      color: kColorTextSecondary,
      height: 1.5,
    );

TextStyle kCaption() => GoogleFonts.inter(
      fontSize: 12,
      fontWeight: FontWeight.w500,
      color: kColorTextMuted,
      letterSpacing: 0.2,
    );

// ── Theme data ─────────────────────────────────────────────────────────
ThemeData buildOlasmTheme() {
  return ThemeData(
    brightness: Brightness.dark,
    scaffoldBackgroundColor: kColorBackground,
    colorScheme: const ColorScheme.dark(
      primary: kColorPrimary,
      secondary: kColorSecondary,
      surface: kColorSurface,
      error: kColorError,
    ),
    textTheme: GoogleFonts.interTextTheme(
      ThemeData(brightness: Brightness.dark).textTheme,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: Colors.transparent,
      elevation: 0,
      foregroundColor: kColorTextPrimary,
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: kColorPrimary,
        foregroundColor: Colors.black87,
        minimumSize: const Size.fromHeight(54),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        textStyle: GoogleFonts.inter(
          fontSize: 15,
          fontWeight: FontWeight.w700,
        ),
      ),
    ),
    dialogTheme: DialogThemeData(
      backgroundColor: kColorSurface,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
    ),
    bottomSheetTheme: const BottomSheetThemeData(
      backgroundColor: kColorSurface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
    ),
  );
}
