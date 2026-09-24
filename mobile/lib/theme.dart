import 'package:flutter/material.dart';

/// Gold focus and calm paper / near-black surfaces. No analytics.
const Color kMatteBlack = Color(0xFF12110E);
const Color kSurface = Color(0xFF1C1B17);
const Color kGold = Color(0xFFC9A227);
const Color kGoldDim = Color(0xFF8A7219);
const Color kIvory = Color(0xFFF4F0E6);
const Color kPaper = Color(0xFFF6F3EC);
const Color kInk = Color(0xFF1C1915);

ThemeData buildAppTheme() => buildDarkTheme();

ThemeData buildLightTheme() {
  return _theme(
    brightness: Brightness.light,
    background: kPaper,
    surface: const Color(0xFFFFFDF8),
    onSurface: kInk,
    mutedFill: const Color(0xFFF3EEE4),
  );
}

ThemeData buildDarkTheme() {
  return _theme(
    brightness: Brightness.dark,
    background: kMatteBlack,
    surface: kSurface,
    onSurface: kIvory,
    mutedFill: const Color(0xFF1A1A1A),
  );
}

ThemeData _theme({
  required Brightness brightness,
  required Color background,
  required Color surface,
  required Color onSurface,
  required Color mutedFill,
}) {
  final scheme = ColorScheme(
    brightness: brightness,
    primary: kGold,
    onPrimary: kMatteBlack,
    secondary: kGoldDim,
    onSecondary: brightness == Brightness.dark ? kIvory : kInk,
    surface: surface,
    onSurface: onSurface,
    error: const Color(0xFFB54A4A),
    onError: kIvory,
  );
  final focusSide = WidgetStateProperty.resolveWith<BorderSide?>((states) {
    if (states.contains(WidgetState.focused)) {
      return const BorderSide(color: kGold, width: 2);
    }
    return null;
  });
  return ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: scheme,
    scaffoldBackgroundColor: background,
    focusColor: kGold,
    appBarTheme: AppBarTheme(
      backgroundColor: background,
      foregroundColor: onSurface,
      elevation: 0,
      centerTitle: false,
    ),
    cardTheme: CardThemeData(
      color: surface,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: Color(0x59C9A227)),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: ButtonStyle(
        backgroundColor: const WidgetStatePropertyAll(kGold),
        foregroundColor: const WidgetStatePropertyAll(kMatteBlack),
        minimumSize: const WidgetStatePropertyAll(Size.fromHeight(52)),
        side: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.focused)) {
            return const BorderSide(color: kInk, width: 2);
          }
          return const BorderSide(color: Color(0xFFA68516));
        }),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: ButtonStyle(side: focusSide),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: mutedFill,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: kGold, width: 2),
      ),
    ),
  );
}
