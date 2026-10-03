import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Guarda el token de refresco en el llavero del sistema: Keystore en
/// Android, Keychain en iOS, libsecret (GNOME Keyring) en Linux.
///
/// El de acceso vive **solo en memoria**, igual que en la web: dura quince
/// minutos y escribirlo en disco solo añadiría un sitio más del que robarlo.
class TokenStore {
  static const _refreshKey = 'refresh_token';

  final _storage = const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  /// Solo en memoria, igual que en la web.
  String? accessToken;

  /// Si el llavero no está disponible (un Linux sin GNOME Keyring, por
  /// ejemplo), el token se guarda solo mientras la app está abierta: se pide
  /// la contraseña al volver a abrirla, pero nunca se escribe en claro.
  String? _respaldo;

  Future<String?> readRefreshToken() async {
    try {
      return await _storage.read(key: _refreshKey) ?? _respaldo;
    } catch (_) {
      return _respaldo;
    }
  }

  Future<void> saveRefreshToken(String token) async {
    _respaldo = token;
    try {
      await _storage.write(key: _refreshKey, value: token);
    } catch (_) {
      // Queda en memoria (ver _respaldo).
    }
  }

  Future<void> clear() async {
    accessToken = null;
    _respaldo = null;
    try {
      await _storage.delete(key: _refreshKey);
    } catch (_) {}
  }
}
