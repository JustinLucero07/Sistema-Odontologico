import 'dart:io';

/// Dónde vive el backend.
///
/// `10.0.2.2` es cómo el emulador de Android ve el `localhost` de la máquina
/// anfitriona; desde un teléfono físico hay que poner la IP de la red local.
/// Se puede sobreescribir al compilar sin tocar el código:
///
///     flutter run --dart-define=API_BASE=http://192.168.1.50:8000
class ApiConfig {
  static const _override = String.fromEnvironment('API_BASE');

  static String get baseUrl {
    if (_override.isNotEmpty) return _override;
    if (Platform.isAndroid) return 'http://10.0.2.2:8000';
    return 'http://localhost:8000';
  }

  static String get apiUrl => '$baseUrl/api/v1';
}
