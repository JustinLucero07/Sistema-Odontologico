import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart' show CupertinoPageTransitionsBuilder;

import '../marca/marca.dart';

/// Los mismos tokens que la web, para que la app no parezca otro producto.
/// El set oscuro está *elegido*, no invertido: una paleta invertida da
/// medios tonos sucios y primarios muertos.
class AppColors {
  // El color principal es el de la marca de cada consulta; el resto de su
  // familia se deriva de él para que todo combine.
  static Color get primary => Marca.actual;
  static Color get primaryDark => tono(Marca.actual, -0.28);
  static Color get mint => tono(Marca.actual, 0.3);
  static const accent = Color(0xFFB9832F);
  static const danger = Color(0xFFB3352B);
  static const success = Color(0xFF2B7A4B);

  // Porcelana: un blanco cálido, como el esmalte, en lugar del gris azulado
  // de hospital. Las tarjetas son blanco puro y se separan del fondo por
  // contraste de temperatura, no por sombras pesadas.
  static const inkLight = Color(0xFF14242B);
  static const baseLight = Color(0xFFF6F4EF);
  static const surfaceLight = Color(0xFFFFFFFF);
  static const lineLight = Color(0xFFE7E3DA);

  static Color get primaryOnDark => tono(Marca.actual, 0.38);
  static Color get mintOnDark => tono(Marca.actual, 0.5);
  static const accentOnDark = Color(0xFFE2B155);
  static const dangerOnDark = Color(0xFFEF7A70);
  static const successOnDark = Color(0xFF5FC98B);

  static const inkDark = Color(0xFFE9EFEE);
  static const baseDark = Color(0xFF0A1315);
  static const surfaceDark = Color(0xFF121E21);
  static const lineDark = Color(0xFF223236);
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

/// Familias tipográficas (declaradas en pubspec.yaml).
const fuenteTitulos = 'Jakarta';
const fuenteTexto = 'Inter';

/// Estilo de título editorial: Jakarta, peso alto y tracking negativo que se
/// aprieta a medida que crece.
TextStyle estiloTitulo(double tamano, {Color? color, FontWeight peso = FontWeight.w700}) =>
    TextStyle(
      fontFamily: fuenteTitulos,
      fontSize: tamano,
      fontWeight: peso,
      height: 1.12,
      letterSpacing: tamano >= 28 ? -0.04 * tamano : (tamano >= 18 ? -0.025 * tamano : -0.01 * tamano),
      color: color,
    );

TextTheme _textos(Color ink) {
  final suave = ink.withValues(alpha: 0.62);
  return TextTheme(
    displaySmall: estiloTitulo(34, color: ink, peso: FontWeight.w800),
    headlineLarge: estiloTitulo(30, color: ink, peso: FontWeight.w800),
    headlineMedium: estiloTitulo(26, color: ink, peso: FontWeight.w800),
    headlineSmall: estiloTitulo(23, color: ink),
    titleLarge: estiloTitulo(20, color: ink),
    titleMedium: estiloTitulo(16, color: ink),
    titleSmall: estiloTitulo(14, color: ink, peso: FontWeight.w600),
    bodyLarge: TextStyle(fontSize: 16, height: 1.45, color: ink),
    bodyMedium: TextStyle(fontSize: 14, height: 1.42, color: ink),
    bodySmall: TextStyle(fontSize: 12.5, height: 1.38, color: suave),
    labelLarge: const TextStyle(fontSize: 14.5, fontWeight: FontWeight.w600, letterSpacing: 0.1),
    labelMedium: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, color: suave),
    labelSmall: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, letterSpacing: 0.3, color: suave),
  );
}

ThemeData _build(Brightness brightness) {
  final dark = brightness == Brightness.dark;
  final primary = dark ? AppColors.primaryOnDark : AppColors.primary;
  final ink = dark ? AppColors.inkDark : AppColors.inkLight;
  final base = dark ? AppColors.baseDark : AppColors.baseLight;
  final surface = dark ? AppColors.surfaceDark : AppColors.surfaceLight;
  final line = dark ? AppColors.lineDark : AppColors.lineLight;

  final scheme =
      ColorScheme.fromSeed(seedColor: primary, brightness: brightness).copyWith(
        primary: primary,
        onPrimary: dark ? const Color(0xFF04201D) : Colors.white,
        secondary: dark ? AppColors.accentOnDark : AppColors.accent,
        surface: surface,
        onSurface: ink,
        surfaceContainerLowest: surface,
        surfaceContainerLow: dark ? const Color(0xFF162427) : const Color(0xFFFBFAF7),
        surfaceContainer: dark ? const Color(0xFF182629) : const Color(0xFFF3F0EA),
        surfaceContainerHigh: dark ? const Color(0xFF1C2C2F) : const Color(0xFFEEEAE2),
        surfaceContainerHighest: dark ? const Color(0xFF223336) : const Color(0xFFE9E5DC),
        outline: line,
        outlineVariant: line,
        error: dark ? AppColors.dangerOnDark : AppColors.danger,
      );

  final radioCampo = BorderRadius.circular(14);

  return ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: scheme,
    fontFamily: fuenteTexto,
    scaffoldBackgroundColor: base,
    canvasColor: base,
    splashFactory: InkSparkle.splashFactory,
    textTheme: _textos(ink),
    iconTheme: IconThemeData(color: ink.withValues(alpha: 0.78), size: 22),
    appBarTheme: AppBarTheme(
      // Transparente: cada barra pone detrás GlassAppBarBackground.
      backgroundColor: Colors.transparent,
      scrolledUnderElevation: 0,
      surfaceTintColor: Colors.transparent,
      foregroundColor: ink,
      elevation: 0,
      centerTitle: false,
      titleTextStyle: estiloTitulo(19, color: ink),
    ),
    cardTheme: CardThemeData(
      color: surface,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(color: line),
      ),
      margin: EdgeInsets.zero,
    ),
    // Campos blancos sobre porcelana, con borde fino que se vuelve del color
    // de la marca al enfocarlos.
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: dark ? const Color(0xFF152225) : Colors.white,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      labelStyle: TextStyle(color: ink.withValues(alpha: 0.6)),
      floatingLabelStyle: TextStyle(color: primary, fontWeight: FontWeight.w600),
      hintStyle: TextStyle(color: ink.withValues(alpha: 0.4)),
      prefixIconColor: ink.withValues(alpha: 0.5),
      border: OutlineInputBorder(borderRadius: radioCampo, borderSide: BorderSide(color: line)),
      enabledBorder: OutlineInputBorder(borderRadius: radioCampo, borderSide: BorderSide(color: line)),
      focusedBorder: OutlineInputBorder(borderRadius: radioCampo, borderSide: BorderSide(color: primary, width: 1.6)),
      errorBorder: OutlineInputBorder(borderRadius: radioCampo, borderSide: BorderSide(color: scheme.error)),
      focusedErrorBorder: OutlineInputBorder(borderRadius: radioCampo, borderSide: BorderSide(color: scheme.error, width: 1.6)),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size.fromHeight(52),
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        textStyle: const TextStyle(fontFamily: fuenteTexto, fontSize: 15, fontWeight: FontWeight.w600, letterSpacing: 0.1),
      ),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: ink,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        backgroundColor: surface,
        side: BorderSide(color: line),
        textStyle: const TextStyle(fontFamily: fuenteTexto, fontWeight: FontWeight.w600),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        textStyle: const TextStyle(fontFamily: fuenteTexto, fontWeight: FontWeight.w600),
      ),
    ),
    floatingActionButtonTheme: FloatingActionButtonThemeData(
      backgroundColor: dark ? primary : AppColors.inkLight,
      foregroundColor: dark ? const Color(0xFF04201D) : Colors.white,
      elevation: 0,
      focusElevation: 0,
      hoverElevation: 0,
      highlightElevation: 0,
      extendedTextStyle: const TextStyle(fontFamily: fuenteTexto, fontWeight: FontWeight.w600, fontSize: 14.5),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: surface,
      selectedColor: primary.withValues(alpha: dark ? 0.24 : 0.1),
      side: BorderSide(color: line),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      labelStyle: TextStyle(fontFamily: fuenteTexto, fontSize: 13, fontWeight: FontWeight.w500, color: ink),
      showCheckmark: false,
    ),
    tabBarTheme: TabBarThemeData(
      labelColor: ink,
      unselectedLabelColor: ink.withValues(alpha: 0.5),
      labelStyle: const TextStyle(fontFamily: fuenteTexto, fontWeight: FontWeight.w600, fontSize: 14),
      unselectedLabelStyle: const TextStyle(fontFamily: fuenteTexto, fontWeight: FontWeight.w500, fontSize: 14),
      indicatorSize: TabBarIndicatorSize.label,
      indicator: UnderlineTabIndicator(
        borderSide: BorderSide(color: primary, width: 2.5),
        borderRadius: BorderRadius.circular(2),
      ),
      dividerColor: line,
    ),
    listTileTheme: ListTileThemeData(
      iconColor: ink.withValues(alpha: 0.6),
      titleTextStyle: TextStyle(fontFamily: fuenteTexto, fontSize: 15, fontWeight: FontWeight.w600, color: ink),
      subtitleTextStyle: TextStyle(fontFamily: fuenteTexto, fontSize: 13, height: 1.35, color: ink.withValues(alpha: 0.6)),
    ),
    popupMenuTheme: PopupMenuThemeData(
      color: surface,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: line),
      ),
      elevation: 6,
      shadowColor: const Color(0x33000000),
    ),
    dialogTheme: DialogThemeData(
      backgroundColor: surface,
      surfaceTintColor: Colors.transparent,
      titleTextStyle: estiloTitulo(20, color: ink),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
    ),
    bottomSheetTheme: BottomSheetThemeData(
      backgroundColor: base,
      surfaceTintColor: Colors.transparent,
      showDragHandle: true,
      dragHandleColor: ink.withValues(alpha: 0.18),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(28))),
    ),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      backgroundColor: dark ? const Color(0xFF223336) : AppColors.inkLight,
      contentTextStyle: const TextStyle(fontFamily: fuenteTexto, color: Colors.white, fontSize: 14),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
    ),
    progressIndicatorTheme: ProgressIndicatorThemeData(color: primary, linearTrackColor: line),
    switchTheme: SwitchThemeData(
      trackOutlineColor: WidgetStateProperty.all(Colors.transparent),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: surface,
      surfaceTintColor: Colors.transparent,
      indicatorColor: primary.withValues(alpha: 0.12),
      height: 68,
      labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
    ),
    dividerTheme: DividerThemeData(color: line, space: 1, thickness: 1),
    pageTransitionsTheme: const PageTransitionsTheme(
      builders: {
        TargetPlatform.android: FadeForwardsPageTransitionsBuilder(),
        TargetPlatform.iOS: CupertinoPageTransitionsBuilder(),
        TargetPlatform.linux: FadeForwardsPageTransitionsBuilder(),
      },
    ),
  );
}

ThemeData lightTheme() => _build(Brightness.light);
ThemeData darkTheme() => _build(Brightness.dark);
