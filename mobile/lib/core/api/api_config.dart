import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ApiConfig {
  static const _fijo = String.fromEnvironment('API_BASE');
  static const _clave = 'servidor_clinica';
  static String? _guardado;

  static String get _desarrollo {
    if (kReleaseMode) return '';
    if (!kIsWeb && Platform.isAndroid) return 'http://10.0.2.2:8000';
    return 'http://localhost:8000';
  }

  static bool get esFijo => _fijo.isNotEmpty;

  static String get baseUrl =>
      _fijo.isNotEmpty ? _fijo : (_guardado ?? _desarrollo);

  static bool get configurado => baseUrl.isNotEmpty;

  static String get apiUrl => '$baseUrl/api/v1';

  /// Lo que se muestra al usuario: solo el dominio.
  static String get servidorVisible =>
      baseUrl.replaceFirst(RegExp(r'^https?://'), '');

  static Future<void> cargar() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      _guardado = prefs.getString(_clave);
    } catch (_) {
      // Sin preferencias se usa la dirección por defecto.
    }
  }

  static String normalizar(String texto) {
    var t = texto.trim().replaceAll(RegExp(r'/+$'), '');
    t = t.replaceFirst(RegExp(r'/api/v1$'), '');
    if (!t.startsWith('http://') && !t.startsWith('https://')) {
      final local = RegExp(
        r'^(localhost|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)',
      ).hasMatch(t);
      t = '${local ? 'http' : 'https'}://$t';
    }
    return t;
  }

  static Future<void> guardar(String texto) async {
    _guardado = normalizar(texto);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_clave, _guardado!);
  }
}
