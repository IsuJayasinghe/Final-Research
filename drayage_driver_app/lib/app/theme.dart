import 'package:flutter/material.dart';

/// Port-optimized theme tailored for in-cab mobile devices and bright outdoor environments.
class AppTheme {
  // Industrial Port Palette
  static const Color primaryDark = Color(0xFF0F172A); // Slate 900
  static const Color surfaceDark = Color(0xFF1E293B); // Slate 800
  static const Color cardDark = Color(0xFF243248); // Slate 750
  static const Color borderSubtle = Color(0xFF334155); // Slate 700

  // High-visibility accents
  static const Color portAmber = Color(0xFFF59E0B); // Terminal Safety Amber
  static const Color portCyan = Color(0xFF06B6D4); // Marine Cyan
  static const Color statusGreen = Color(
    0xFF10B981,
  ); // Emerald Completed/Active
  static const Color statusYellow = Color(0xFFFBBF24); // Pending/Travelling
  static const Color statusRed = Color(0xFFEF4444); // Urgent / Attention
  static const Color textPrimary = Color(0xFFF8FAFC);
  static const Color textSecondary = Color(0xFF94A3B8);

  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: primaryDark,
      primaryColor: portAmber,
      colorScheme: const ColorScheme.dark(
        primary: portAmber,
        secondary: portCyan,
        surface: surfaceDark,
        error: statusRed,
        onPrimary: Colors.black,
        onSecondary: Colors.black,
        onSurface: textPrimary,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: surfaceDark,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: textPrimary,
          fontSize: 19,
          fontWeight: FontWeight.bold,
          letterSpacing: 0.3,
        ),
        iconTheme: IconThemeData(color: textPrimary),
      ),
      cardTheme: CardThemeData(
        color: surfaceDark,
        elevation: 2,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: borderSubtle, width: 1),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: portAmber,
          foregroundColor: Colors.black,
          minimumSize: const Size.fromHeight(
            52,
          ), // Large touch targets for truck drivers
          textStyle: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
            letterSpacing: 0.5,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: portCyan,
          side: const BorderSide(color: portCyan, width: 1.5),
          minimumSize: const Size.fromHeight(50),
          textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: cardDark,
        hintStyle: const TextStyle(color: textSecondary),
        labelStyle: const TextStyle(color: portAmber),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 16,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: borderSubtle),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: borderSubtle),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: portAmber, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: statusRed),
        ),
      ),
      dividerTheme: const DividerThemeData(
        color: borderSubtle,
        thickness: 1,
        space: 24,
      ),
    );
  }
}
