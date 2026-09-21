import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Guarda el token de refresco en el llavero de Android / Keychain de iOS.
///
/// El de acceso vive **solo en memoria**, igual que en la web: dura quince
/// minutos y escribirlo en disco solo añadiría un sitio más del que robarlo.
class TokenStore {
  static const _refreshKey = 'refresh_token';

  final _storage = const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  /// Solo en memoria, igual que en la web: dura quince minutos y escribirlo
  /// en disco solo añadiría un sitio más del que robarlo.
  String? accessToken;

  Future<String?> readRefreshToken() => _storage.read(key: _refreshKey);

  Future<void> saveRefreshToken(String token) =>
      _storage.write(key: _refreshKey, value: token);

  Future<void> clear() async {
    accessToken = null;
    await _storage.delete(key: _refreshKey);
  }
}
