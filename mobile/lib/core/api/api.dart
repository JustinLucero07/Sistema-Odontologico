import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/auth_controller.dart';
import 'repositorios.dart';

/// Acceso directo a la API para los módulos de gestión.
///
/// Cada respuesta que no es 2xx se convierte en [ErrorApi] con el mensaje que
/// dio el servidor: «la caja ya está abierta», «quedan 2 en existencia»… Esa
/// frase es justo lo que la persona necesita leer, no un «error 409».
class Api {
  Api(this._dio);
  final Dio _dio;

  Future<dynamic> get(String ruta, {Map<String, dynamic>? query}) =>
      _enviar(() => _dio.get(ruta, queryParameters: _limpiar(query)));

  Future<dynamic> post(String ruta, [Object? datos]) =>
      _enviar(() => _dio.post(ruta, data: datos));

  Future<dynamic> put(String ruta, [Object? datos]) =>
      _enviar(() => _dio.put(ruta, data: datos));

  Future<dynamic> delete(String ruta) => _enviar(() => _dio.delete(ruta));

  /// Lista: el servidor a veces responde `{items: [...]}` y a veces `[...]`.
  Future<List<Map<String, dynamic>>> lista(
    String ruta, {
    Map<String, dynamic>? query,
  }) async {
    final data = await get(ruta, query: query);
    final items = data is Map && data['items'] is List
        ? data['items'] as List
        : (data as List? ?? []);
    return items.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> mapa(
    String ruta, {
    Map<String, dynamic>? query,
  }) async => (await get(ruta, query: query) as Map).cast<String, dynamic>();

  Future<dynamic> _enviar(Future<Response<dynamic>> Function() llamada) async {
    try {
      final r = await llamada();
      final code = r.statusCode ?? 0;
      if (code >= 200 && code < 300) return r.data;
      throw ErrorApi(mensajeDeError(r.data, code));
    } on DioException catch (e) {
      if (e.response != null) {
        throw ErrorApi(
          mensajeDeError(e.response!.data, e.response!.statusCode ?? 0),
        );
      }
      throw ErrorApi('No se pudo conectar con el servidor de la clínica.');
    }
  }

  Map<String, dynamic>? _limpiar(Map<String, dynamic>? q) => q == null
      ? null
      : {
          for (final e in q.entries)
            if (e.value != null && '${e.value}'.isNotEmpty) e.key: e.value,
        };
}

/// El `detail` del servidor en una frase legible. Los errores de validación
/// llegan como lista; se toma el primero y se quita la jerga técnica.
String mensajeDeError(dynamic data, int code) {
  final detail = data is Map ? data['detail'] : null;
  if (detail is String) return detail;
  if (detail is List && detail.isNotEmpty) {
    final primero = detail.first;
    if (primero is Map && primero['msg'] is String) {
      final msg = (primero['msg'] as String).replaceFirst('Value error, ', '');
      final campo =
          primero['loc'] is List && (primero['loc'] as List).isNotEmpty
          ? '${(primero['loc'] as List).last}'
          : null;
      return campo == null || campo == 'body' ? msg : '$msg ($campo)';
    }
  }
  return switch (code) {
    403 => 'Su usuario no tiene permiso para esto.',
    404 => 'No se encontró el registro.',
    429 => 'Demasiados intentos. Espere un momento.',
    _ => 'No se pudo completar la operación.',
  };
}

final apiProvider = Provider((ref) => Api(ref.watch(apiClientProvider).dio));

/// Convierte lo que manda el servidor ("12.50", 12.5, null) en número.
double numero(dynamic valor) =>
    valor is num ? valor.toDouble() : double.tryParse('${valor ?? ''}') ?? 0;

/// Formulario multiparte con un archivo y sus datos.
Future<FormData> formDataDesde(
  String ruta,
  Map<String, dynamic> campos,
) async => FormData.fromMap({
  'file': await MultipartFile.fromFile(ruta),
  for (final e in campos.entries)
    if (e.value != null) e.key: '${e.value}',
});
