import 'dart:async';

import 'package:dio/dio.dart';

import 'api_config.dart';
import 'token_store.dart';

/// Cliente HTTP con refresco automático.
///
/// El navegador guarda la cookie de refresco solo; aquí no hay navegador, así
/// que el token viaja en el cuerpo y se guarda en el llavero. Lo demás es
/// igual que en la web: al recibir un 401 se intenta **un** refresco y se
/// reintenta la petición; si el refresco también falla, se cierra la sesión.
class ApiClient {
  ApiClient(this.tokens) {
    dio = Dio(
      BaseOptions(
        baseUrl: ApiConfig.apiUrl,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 30),
        // Los errores del servidor traen un `detail` en español que es mucho
        // más útil que cualquier texto genérico nuestro, así que no se tratan
        // como excepción de transporte: se leen.
        validateStatus: (code) => code != null && code < 500,
      ),
    );

    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          // Le dice al servidor que este cliente no tiene cookies y necesita el
          // token de refresco en el cuerpo. Un navegador nunca la envía.
          options.headers['X-Token-Delivery'] = 'body';
          final token = tokens.accessToken;
          if (token != null && !_isAuthEndpoint(options.path)) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
        onResponse: (response, handler) async {
          if (response.statusCode != 401 ||
              _isAuthEndpoint(response.requestOptions.path)) {
            return handler.next(response);
          }
          final refreshed = await _refresh();
          if (!refreshed) {
            onSessionExpired?.call();
            return handler.next(response);
          }
          try {
            final retried = await _retry(response.requestOptions);
            return handler.resolve(retried);
          } on DioException catch (error) {
            return handler.next(error.response ?? response);
          }
        },
      ),
    );
  }

  late final Dio dio;
  final TokenStore tokens;

  /// Lo llama el cliente cuando ni el refresco sirve. La capa de estado lo usa
  /// para mandar al usuario al login sin que cada pantalla tenga que mirarlo.
  void Function()? onSessionExpired;

  bool _isAuthEndpoint(String path) =>
      path.contains('/auth/login') || path.contains('/auth/refresh');

  Completer<bool>? _refreshing;

  /// Si llegan tres 401 a la vez, se refresca **una** sola vez y las tres
  /// esperan al mismo resultado. Refrescar en paralelo rota el token contra sí
  /// mismo e invalida la sesión entera.
  Future<bool> _refresh() {
    final inFlight = _refreshing;
    if (inFlight != null) return inFlight.future;

    final completer = Completer<bool>();
    _refreshing = completer;
    _doRefresh().then((ok) {
      _refreshing = null;
      completer.complete(ok);
    });
    return completer.future;
  }

  Future<bool> _doRefresh() async {
    final refreshToken = await tokens.readRefreshToken();
    if (refreshToken == null) return false;
    try {
      final response = await Dio(
        BaseOptions(baseUrl: ApiConfig.apiUrl),
      ).post('/auth/refresh', data: {'refresh_token': refreshToken});
      if (response.statusCode != 200) return false;
      tokens.accessToken = response.data['access_token'] as String;
      final rotated = response.data['refresh_token'] as String?;
      if (rotated != null) await tokens.saveRefreshToken(rotated);
      return true;
    } on DioException {
      return false;
    }
  }

  Future<Response<dynamic>> _retry(RequestOptions options) {
    return dio.request<dynamic>(
      options.path,
      data: options.data,
      queryParameters: options.queryParameters,
      options: Options(method: options.method, headers: options.headers),
    );
  }
}

/// Convierte la respuesta del servidor en un mensaje que se puede enseñar.
String messageFrom(Response<dynamic>? response, String fallback) {
  final detail = response?.data is Map ? response!.data['detail'] : null;
  if (detail is String) return detail;
  return fallback;
}
