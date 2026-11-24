import 'dart:async';

import 'package:dio/dio.dart';

import 'api_config.dart';
import 'token_store.dart';

class ApiClient {
  ApiClient(this.tokens) {
    dio = Dio(
      BaseOptions(
        baseUrl: ApiConfig.apiUrl,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 30),
        validateStatus: (code) => code != null && code < 500,
      ),
    );

    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          options.headers['X-Token-Delivery'] = 'body';
          final token = tokens.accessToken;
          // La dirección del servidor puede cambiarse desde el login.
          options.baseUrl = ApiConfig.apiUrl;
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

  void Function()? onSessionExpired;

  bool _isAuthEndpoint(String path) =>
      path.contains('/auth/login') || path.contains('/auth/refresh');

  Completer<bool>? _refreshing;

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

String messageFrom(Response<dynamic>? response, String fallback) {
  final detail = response?.data is Map ? response!.data['detail'] : null;
  if (detail is String) return detail;
  return fallback;
}
