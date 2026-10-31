import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../api/token_store.dart';
import '../models/usuario.dart';
import '../notificaciones/avisos_citas.dart';
import '../offline/sin_conexion.dart';

final tokenStoreProvider = Provider<TokenStore>((ref) => TokenStore());

/// Trabajo sin conexión (copia local y cola de cambios).
final sinConexionProvider = ChangeNotifierProvider<SinConexion>((ref) => SinConexion());

final apiClientProvider = Provider<ApiClient>((ref) {
  final client = ApiClient(ref.watch(tokenStoreProvider));
  client.onSessionExpired = () =>
      ref.read(authProvider.notifier).cerrarSesionLocal();
  ref.read(sinConexionProvider).iniciar(client.dio);
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
      // Sin red no se cierra la sesión: se entra con la última guardada y
      // se trabaja con la copia local hasta que vuelva la conexión.
      final guardado = await _ref.read(sinConexionProvider).usuarioGuardado();
      if (guardado != null) {
        state = AuthState(estado: EstadoSesion.autenticado, usuario: Usuario.fromJson(guardado));
      } else {
        state = const AuthState(estado: EstadoSesion.anonimo);
      }
    }
  }

  Future<bool> iniciarSesion(String email, String password) async {
    // No se pasa a «cargando»: eso reemplazaría el login por la pantalla de
    // arranque y, si falla, se perdería lo escrito. El botón ya muestra la
    // espera.
    state = state.copyWith(error: null);
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
    final datos = response.data as Map<String, dynamic>;
    state = AuthState(estado: EstadoSesion.autenticado, usuario: Usuario.fromJson(datos));
    final local = _ref.read(sinConexionProvider);
    await local.guardarUsuario(datos);
    // Lo esencial para trabajar sin red: pacientes, la agenda de la semana y
    // el panel. Lo demás se guarda a medida que se consulta.
    unawaited(_precargar());
  }

  Future<void> _precargar() async {
    final dio = _api.dio;
    try {
      await dio.get('/patients');
      await dio.get('/dashboard/summary');
      final hoy = DateTime.now();
      for (var d = 0; d < 7; d++) {
        final desde = DateTime(hoy.year, hoy.month, hoy.day).add(Duration(days: d));
        await dio.get('/appointments', queryParameters: {
          'from': desde.toUtc().toIso8601String(),
          'to': desde.add(const Duration(days: 1)).toUtc().toIso8601String(),
        });
      }
    } catch (_) {
      // Es solo una precarga: si falla, se guarda lo que se vaya viendo.
    }
    // Avisos de citas en el teléfono (pide permiso la primera vez).
    await AvisosCitas.instancia.pedirPermiso();
    await AvisosCitas.instancia.actualizar(dio);
  }

  /// Registra la aceptación del acuerdo y relee el usuario, que ya no lo
  /// tendrá pendiente.
  Future<void> aceptarConfidencialidad() async {
    await _api.dio.post('/auth/confidentiality');
    await _cargarUsuario();
  }

  /// Cambia la contraseña propia. El servidor cierra las demás sesiones y
  /// devuelve tokens nuevos para esta. Devuelve el mensaje de error, o nulo
  /// si salió bien.
  Future<String?> cambiarClave(String actual, String nueva) async {
    try {
      final response = await _api.dio.post(
        '/auth/change-password',
        data: {'current_password': actual, 'new_password': nueva},
      );
      if (response.statusCode != 200) {
        return messageFrom(
          response,
          response.statusCode == 429
              ? 'Demasiados intentos. Espere un minuto.'
              : 'No se pudo cambiar la contraseña. Revise que cumpla las reglas.',
        );
      }
      _tokens.accessToken = response.data['access_token'] as String;
      final refresh = response.data['refresh_token'] as String?;
      if (refresh != null) await _tokens.saveRefreshToken(refresh);
      await _cargarUsuario();
      return null;
    } on DioException {
      return 'No se pudo conectar con el servidor de la clínica.';
    }
  }

  Future<void> cerrarSesion() async {
    final refresh = await _tokens.readRefreshToken();
    try {
      await _api.dio.post('/auth/logout', data: {'refresh_token': refresh});
    } on DioException {
      // Si el servidor no contesta, la sesión se cierra en el dispositivo de
      // todas formas: dejar al usuario dentro porque falló la red sería peor.
    }
    // Al salir a propósito no queda nada de esta persona en el teléfono.
    await _ref.read(sinConexionProvider).olvidarTodo();
    await AvisosCitas.instancia.borrarTodo();
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
