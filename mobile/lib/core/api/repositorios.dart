import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/auth_controller.dart';
import '../models/cita.dart';
import '../models/paciente.dart';

/// Error con el mensaje que el servidor realmente dio. Las pantallas lo
/// enseñan tal cual: el backend distingue «no hay existencias suficientes:
/// quedan 2» de un fallo genérico, y esa diferencia es la respuesta.
class ErrorApi implements Exception {
  ErrorApi(this.mensaje);
  final String mensaje;
  @override
  String toString() => mensaje;
}

Never _lanzar(Response<dynamic> r, String porDefecto) {
  final detail = r.data is Map ? r.data['detail'] : null;
  throw ErrorApi(detail is String ? detail : porDefecto);
}

class AgendaRepo {
  AgendaRepo(this._dio);
  final Dio _dio;

  Future<List<Cita>> citasDelDia(DateTime dia) async {
    final desde = DateTime(dia.year, dia.month, dia.day);
    final hasta = desde.add(const Duration(days: 1));
    // El endpoint usa los alias `from` y `to`.
    final r = await _dio.get(
      '/appointments',
      queryParameters: {
        'from': desde.toUtc().toIso8601String(),
        'to': hasta.toUtc().toIso8601String(),
      },
    );
    if (r.statusCode != 200) _lanzar(r, 'No se pudo cargar la agenda');
    return (r.data as List)
        .map((e) => Cita.fromJson(e as Map<String, dynamic>))
        .toList()
      ..sort((a, b) => a.inicio.compareTo(b.inicio));
  }

  Future<void> cambiarEstado(
    String citaId,
    String estado, {
    String? motivo,
  }) async {
    final r = await _dio.put(
      '/appointments/$citaId/status',
      data: {
        'status': estado,
        if (motivo != null) 'cancellation_reason': motivo,
      },
    );
    if (r.statusCode != 200) _lanzar(r, 'No se pudo cambiar el estado');
  }
}

class PacientesRepo {
  PacientesRepo(this._dio);
  final Dio _dio;

  Future<List<PacienteResumen>> buscar(String termino) async {
    final r = await _dio.get(
      '/patients',
      queryParameters: {
        if (termino.trim().isNotEmpty) 'search': termino.trim(),
      },
    );
    if (r.statusCode != 200) _lanzar(r, 'No se pudo buscar pacientes');
    final data = r.data;
    final items = data is Map && data.containsKey('items')
        ? data['items'] as List
        : data as List;
    return items
        .map((e) => PacienteResumen.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<Map<String, dynamic>> ficha(String pacienteId) async {
    final r = await _dio.get('/patients/$pacienteId');
    if (r.statusCode != 200) _lanzar(r, 'No se pudo cargar el paciente');
    return r.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>?> odontograma(String pacienteId) async {
    final r = await _dio.get('/patients/$pacienteId/odontogram');
    if (r.statusCode != 200) _lanzar(r, 'No se pudo cargar el odontograma');
    return r.data as Map<String, dynamic>?;
  }

  Future<Map<String, dynamic>> cuenta(String pacienteId) async {
    final r = await _dio.get('/patients/$pacienteId/account');
    if (r.statusCode != 200) {
      _lanzar(r, 'No se pudo cargar el estado de cuenta');
    }
    return r.data as Map<String, dynamic>;
  }

  Future<void> subirImagen({
    required String pacienteId,
    required String rutaArchivo,
    required String titulo,
    required String tipo,
    String? piezas,
  }) async {
    final form = FormData.fromMap({
      'file': await MultipartFile.fromFile(rutaArchivo),
      'title': titulo,
      'image_type': tipo,
      if (piezas != null && piezas.isNotEmpty) 'fdi_numbers': piezas,
    });
    final r = await _dio.post('/patients/$pacienteId/images', data: form);
    if (r.statusCode != 201) _lanzar(r, 'No se pudo subir la imagen');
  }

  Future<void> registrarEvolucion({
    required String pacienteId,
    required String procedimiento,
    String? piezas,
    String? indicaciones,
  }) async {
    final r = await _dio.post(
      '/patients/$pacienteId/evolutions',
      data: {
        'procedure': procedimiento,
        if (piezas != null && piezas.isNotEmpty) 'fdi_numbers': piezas,
        if (indicaciones != null && indicaciones.isNotEmpty)
          'instructions': indicaciones,
      },
    );
    if (r.statusCode != 201) _lanzar(r, 'No se pudo registrar la evolución');
  }
}

class PanelRepo {
  PanelRepo(this._dio);
  final Dio _dio;

  Future<Map<String, dynamic>> resumen() async {
    final r = await _dio.get('/dashboard/summary');
    if (r.statusCode != 200) _lanzar(r, 'No se pudo cargar el panel');
    return r.data as Map<String, dynamic>;
  }
}

final agendaRepoProvider = Provider(
  (ref) => AgendaRepo(ref.watch(apiClientProvider).dio),
);
final pacientesRepoProvider = Provider(
  (ref) => PacientesRepo(ref.watch(apiClientProvider).dio),
);
final panelRepoProvider = Provider(
  (ref) => PanelRepo(ref.watch(apiClientProvider).dio),
);
