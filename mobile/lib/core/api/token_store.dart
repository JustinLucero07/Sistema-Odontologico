import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class TokenStore {
  static const _refreshKey = 'refresh_token';

  final _storage = const FlutterSecureStorage(
    aOptions: AndroidOptions(),
  );

  /// Solo en memoria, igual que en la web.
  String? accessToken;

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
