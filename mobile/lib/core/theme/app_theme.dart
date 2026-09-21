import 'package:flutter/material.dart';

/// Los mismos tokens que la web, para que la app no parezca otro producto.
/// El set oscuro está *elegido*, no invertido: una paleta invertida da
/// medios tonos sucios y primarios muertos.
class AppColors {
  static const primary = Color(0xFF0D7F76);
  static const primaryDark = Color(0xFF095C55);
  static const mint = Color(0xFF2FBFAE);
  static const accent = Color(0xFFB9832F);
  static const danger = Color(0xFFB3352B);
  static const success = Color(0xFF2B7A4B);

  static const inkLight = Color(0xFF0F2427);
  static const baseLight = Color(0xFFEEF3F4);
  static const surfaceLight = Color(0xFFFFFFFF);

  static const primaryOnDark = Color(0xFF34D3C0);
  static const mintOnDark = Color(0xFF5EE0CE);
  static const accentOnDark = Color(0xFFE2B155);
  static const dangerOnDark = Color(0xFFEF7A70);
  static const successOnDark = Color(0xFF5FC98B);

  static const inkDark = Color(0xFFE7F1F1);
  static const baseDark = Color(0xFF081416);
  static const surfaceDark = Color(0xFF112124);
}

/// Colores de estado de cita. Vienen validados para daltonismo desde la web
/// (peor par adyacente ΔE 9,5 protan / 21,3 visión normal), así que se copian
/// tal cual en lugar de elegirse otra vez a ojo.
class StatusColors {
  static const Map<String, Color> light = {
    'programada': Color(0xFF22B8CF),
    'confirmada': Color(0xFF2B8A3E),
    'en_espera': Color(0xFFF08C00),
    'en_atencion': Color(0xFF3B5BDB),
    'atendida': Color(0xFF0CA678),
    'cancelada': Color(0xFFC92A2A),
    'no_asistio': Color(0xFF9C36B5),
  };

  /// Tres pasos del set claro caen por debajo de 3:1 sobre el fondo oscuro,
  /// así que índigo, rojo y morado se re-escalan. El resto se mantiene: un
  /// estado no debería cambiar de identidad al cambiar el tema.
  static const Map<String, Color> dark = {
    'programada': Color(0xFF22B8CF),
    'confirmada': Color(0xFF2B8A3E),
    'en_espera': Color(0xFFF08C00),
    'en_atencion': Color(0xFF486BEC),
    'atendida': Color(0xFF0CA678),
    'cancelada': Color(0xFFD73A36),
    'no_asistio': Color(0xFFAE49C7),
  };

  static Color of(BuildContext context, String status) {
    final map = Theme.of(context).brightness == Brightness.dark ? dark : light;
    return map[status] ?? Colors.grey;
  }
}

const Map<String, String> statusLabels = {
  'programada': 'Programada',
  'confirmada': 'Confirmada',
  'en_espera': 'En espera',
  'en_atencion': 'En atención',
  'atendida': 'Atendida',
  'cancelada': 'Cancelada',
  'no_asistio': 'No asistió',
};

ThemeData _build(Brightness brightness) {
  final dark = brightness == Brightness.dark;
  final primary = dark ? AppColors.primaryOnDark : AppColors.primary;
  final ink = dark ? AppColors.inkDark : AppColors.inkLight;
  final base = dark ? AppColors.baseDark : AppColors.baseLight;
  final surface = dark ? AppColors.surfaceDark : AppColors.surfaceLight;

  final scheme =
      ColorScheme.fromSeed(seedColor: primary, brightness: brightness).copyWith(
        primary: primary,
        surface: surface,
        error: dark ? AppColors.dangerOnDark : AppColors.danger,
      );

  return ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: scheme,
    scaffoldBackgroundColor: base,
    // El tracking es específico del tamaño: se aprieta al crecer, y el cuerpo
    // se queda cerca de cero.
    textTheme: Typography.material2021().black
        .apply(bodyColor: ink, displayColor: ink)
        .copyWith(
          headlineMedium: TextStyle(
            fontWeight: FontWeight.w700,
            letterSpacing: -0.6,
            color: ink,
          ),
          titleLarge: TextStyle(
            fontWeight: FontWeight.w700,
            letterSpacing: -0.3,
            color: ink,
          ),
          titleMedium: TextStyle(fontWeight: FontWeight.w600, color: ink),
        ),
    appBarTheme: AppBarTheme(
      backgroundColor: base,
      surfaceTintColor: Colors.transparent,
      foregroundColor: ink,
      elevation: 0,
      centerTitle: false,
      titleTextStyle: TextStyle(
        fontSize: 20,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.4,
        color: ink,
      ),
    ),
    cardTheme: CardThemeData(
      color: surface,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: ink.withValues(alpha: 0.08)),
      ),
      margin: EdgeInsets.zero,
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: surface,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: ink.withValues(alpha: 0.14)),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: ink.withValues(alpha: 0.14)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: primary, width: 2),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size.fromHeight(52),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: surface,
      surfaceTintColor: Colors.transparent,
      indicatorColor: primary.withValues(alpha: 0.16),
      height: 68,
      labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
    ),
    dividerTheme: DividerThemeData(
      color: ink.withValues(alpha: 0.08),
      space: 1,
    ),
  );
}

ThemeData lightTheme() => _build(Brightness.light);
ThemeData darkTheme() => _build(Brightness.dark);
