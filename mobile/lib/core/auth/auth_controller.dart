import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../api/token_store.dart';
import '../models/usuario.dart';

final tokenStoreProvider = Provider<TokenStore>((ref) => TokenStore());

final apiClientProvider = Provider<ApiClient>((ref) {
  final client = ApiClient(ref.watch(tokenStoreProvider));
  client.onSessionExpired = () =>
      ref.read(authProvider.notifier).cerrarSesionLocal();
  return client;
});

/// Estado de la sesión.
///
/// `cargando` es un tercer estado a propósito: al abrir la app hay un momento
/// en que no se sabe si hay sesión, y dibujar el login durante ese momento
/// hace parpadear la pantalla a quien sí la tiene.
enum EstadoSesion { cargando, autenticado, anonimo }

class AuthState {
  const AuthState({required this.estado, this.usuario, this.error});

  final EstadoSesion estado;
  final Usuario? usuario;
  final String? error;

  AuthState copyWith({EstadoSesion? estado, Usuario? usuario, String? error}) =>
      AuthState(
        estado: estado ?? this.estado,
        usuario: usuario ?? this.usuario,
        error: error,
      );
}

class AuthController extends StateNotifier<AuthState> {
  AuthController(this._ref)
    : super(const AuthState(estado: EstadoSesion.cargando));

  final Ref _ref;

  ApiClient get _api => _ref.read(apiClientProvider);
  TokenStore get _tokens => _ref.read(tokenStoreProvider);

  /// Al abrir la app se intenta revivir la sesión con el token del llavero.
  /// Si no se puede, se cae al login sin ruido: un token caducado es lo normal
  /// después de una semana, no un error que mostrar.
  Future<void> restaurarSesion() async {
    final refresh = await _tokens.readRefreshToken();
    if (refresh == null) {
      state = const AuthState(estado: EstadoSesion.anonimo);
      return;
    }
    try {
      final response = await _api.dio.post(
        '/auth/refresh',
        data: {'refresh_token': refresh},
      );
      if (response.statusCode != 200) {
        await _tokens.clear();
        state = const AuthState(estado: EstadoSesion.anonimo);
        return;
      }
      _tokens.accessToken = response.data['access_token'] as String;
      final rotado = response.data['refresh_token'] as String?;
      if (rotado != null) await _tokens.saveRefreshToken(rotado);
      await _cargarUsuario();
    } on DioException {
      await _tokens.clear();
      state = const AuthState(estado: EstadoSesion.anonimo);
    }
  }

  Future<bool> iniciarSesion(String email, String password) async {
    state = state.copyWith(estado: EstadoSesion.cargando, error: null);
    try {
      final response = await _api.dio.post(
        '/auth/login',
        data: {'email': email.trim(), 'password': password},
      );
      if (response.statusCode != 200) {
        state = AuthState(
          estado: EstadoSesion.anonimo,
          // El servidor distingue «credenciales inválidas» de «cuenta
          // bloqueada por intentos»; esa diferencia le importa a quien la lee.
          error: messageFrom(response, 'No se pudo iniciar sesión'),
        );
        return false;
      }
      _tokens.accessToken = response.data['access_token'] as String;
      final refresh = response.data['refresh_token'] as String?;
      if (refresh != null) await _tokens.saveRefreshToken(refresh);
      await _cargarUsuario();
      return state.estado == EstadoSesion.autenticado;
    } on DioException catch (e) {
      state = AuthState(
        estado: EstadoSesion.anonimo,
        error:
            e.type == DioExceptionType.connectionError ||
                e.type == DioExceptionType.connectionTimeout
            ? 'No se pudo conectar con el servidor de la clínica.'
            : 'No se pudo iniciar sesión.',
      );
      return false;
    }
  }

  Future<void> _cargarUsuario() async {
    final response = await _api.dio.get('/auth/me');
    if (response.statusCode != 200) {
      state = const AuthState(estado: EstadoSesion.anonimo);
      return;
    }
    state = AuthState(
      estado: EstadoSesion.autenticado,
      usuario: Usuario.fromJson(response.data as Map<String, dynamic>),
    );
  }

  Future<void> cerrarSesion() async {
    final refresh = await _tokens.readRefreshToken();
    try {
      await _api.dio.post('/auth/logout', data: {'refresh_token': refresh});
    } on DioException {
      // Si el servidor no contesta, la sesión se cierra en el dispositivo de
      // todas formas: dejar al usuario dentro porque falló la red sería peor.
    }
    await cerrarSesionLocal();
  }

  Future<void> cerrarSesionLocal() async {
    await _tokens.clear();
    state = const AuthState(estado: EstadoSesion.anonimo);
  }
}

final authProvider = StateNotifierProvider<AuthController, AuthState>(
  (ref) => AuthController(ref),
);
