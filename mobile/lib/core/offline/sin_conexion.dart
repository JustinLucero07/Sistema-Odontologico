import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';

/// Trabajo sin conexión.
///
/// - Todo lo que se consulta con red se guarda en el teléfono; sin red, la
///   app muestra esa copia.
/// - Los cambios hechos sin red (editar un paciente, agendar, anotar una
///   evolución…) se guardan en una cola, se ven al instante en pantalla y se
///   suben solos, en orden, cuando vuelve la conexión.
/// - Cada cambio lleva una llave única (Idempotency-Key): si la red se cortó
///   justo después de que el servidor lo guardara, al reenviarlo no se
///   duplica.
/// - Hay cosas que solo tienen sentido con el servidor delante: facturar ante
///   el SRI, subir fotos, enviar mensajes, iniciar sesión. Esas no se encolan.

/// Rutas que nunca se encolan (necesitan al servidor en ese momento).
const _soloEnLinea = [
  '/auth/',
  '/invoices',
  '/invoicing',
  '/mail/',
  '/sign-link',
  '/public/',
  '/messaging/',
  '/portal',
  '/ai/',
  '/finance/cash-session',
];

class Pendiente {
  Pendiente({
    required this.id,
    required this.metodo,
    required this.ruta,
    required this.datos,
    required this.query,
    required this.creado,
    this.idTemporal,
    this.error,
  });

  final String id; // también es la Idempotency-Key
  final String metodo;
  String ruta;
  dynamic datos;
  final Map<String, dynamic>? query;
  final DateTime creado;

  /// Si es una creación, el id provisional con que se muestra hasta subirla.
  final String? idTemporal;

  /// Motivo por el que el servidor lo rechazó (queda como conflicto).
  String? error;

  Map<String, dynamic> toJson() => {
    'id': id,
    'metodo': metodo,
    'ruta': ruta,
    'datos': datos,
    'query': query,
    'creado': creado.toIso8601String(),
    'idTemporal': idTemporal,
    'error': error,
  };

  factory Pendiente.fromJson(Map<String, dynamic> j) => Pendiente(
    id: j['id'] as String,
    metodo: j['metodo'] as String,
    ruta: j['ruta'] as String,
    datos: j['datos'],
    query: (j['query'] as Map?)?.cast<String, dynamic>(),
    creado: DateTime.parse(j['creado'] as String),
    idTemporal: j['idTemporal'] as String?,
    error: j['error'] as String?,
  );

  /// Descripción legible para la lista de cambios pendientes.
  String get descripcion {
    final partes = ruta.split('/').where((p) => p.isNotEmpty).toList();
    const nombres = {
      'patients': 'paciente',
      'appointments': 'cita',
      'evolutions': 'evolución',
      'diagnoses': 'diagnóstico',
      'prescriptions': 'receta',
      'treatment-plans': 'plan de tratamiento',
      'budgets': 'presupuesto',
      'charges': 'cargo',
      'payments': 'cobro',
      'consents': 'consentimiento',
      'odontogram': 'odontograma',
      'periodontogram': 'periodontograma',
      'medical-history': 'historia clínica',
      'inventory': 'inventario',
      'laboratory': 'laboratorio',
      'expenses': 'gasto',
    };
    String? que;
    for (final p in partes.reversed) {
      if (nombres.containsKey(p)) {
        que = nombres[p];
        break;
      }
    }
    final accion = switch (metodo) {
      'POST' when partes.last == 'status' => 'Cambiar estado de',
      'POST' when partes.last == 'void' => 'Anular',
      'POST' => 'Crear',
      'PUT' || 'PATCH' => 'Editar',
      'DELETE' => 'Eliminar',
      _ => metodo,
    };
    return '$accion ${que ?? 'registro'}';
  }
}

String nuevaLlave() {
  final r = Random.secure();
  final b = List<int>.generate(16, (_) => r.nextInt(256));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  String h(int i, int j) => b.sublist(i, j).map((x) => x.toRadixString(16).padLeft(2, '0')).join();
  return '${h(0, 4)}-${h(4, 6)}-${h(6, 8)}-${h(8, 10)}-${h(10, 16)}';
}

/// Almacén en archivos: una copia por consulta y la cola de cambios. En la
/// versión web (solo para pruebas) vive en memoria.
class Almacen {
  Directory? _dir;
  final Map<String, String> _memoria = {};
  Future<void>? _apertura;

  Future<void> abrir() => _apertura ??= _abrir();

  Future<void> _abrir() async {
    if (kIsWeb) return;
    try {
      final base = await getApplicationSupportDirectory();
      _dir = Directory('${base.path}/sin_conexion');
      await _dir!.create(recursive: true);
    } catch (_) {
      _dir = null; // sin disco, se trabaja en memoria
    }
  }

  String _archivo(String clave) => base64Url.encode(utf8.encode(clave)).replaceAll('=', '');

  Future<String?> leer(String clave) async {
    await abrir();
    if (_dir == null) return _memoria[clave];
    final f = File('${_dir!.path}/${_archivo(clave)}');
    return await f.exists() ? f.readAsString() : null;
  }

  Future<void> escribir(String clave, String valor) async {
    await abrir();
    if (_dir == null) {
      _memoria[clave] = valor;
      return;
    }
    await File('${_dir!.path}/${_archivo(clave)}').writeAsString(valor, flush: true);
  }

  Future<void> borrar(String clave) async {
    await abrir();
    if (_dir == null) {
      _memoria.remove(clave);
      return;
    }
    final f = File('${_dir!.path}/${_archivo(clave)}');
    if (await f.exists()) await f.delete();
  }

  /// Claves guardadas (decodificadas) que empiezan por [prefijo].
  Future<List<String>> claves(String prefijo) async {
    await abrir();
    if (_dir == null) return _memoria.keys.where((k) => k.startsWith(prefijo)).toList();
    final salida = <String>[];
    await for (final e in _dir!.list()) {
      final nombre = e.uri.pathSegments.last;
      try {
        final relleno = '=' * ((4 - nombre.length % 4) % 4);
        final clave = utf8.decode(base64Url.decode(nombre + relleno));
        if (clave.startsWith(prefijo)) salida.add(clave);
      } catch (_) {}
    }
    return salida;
  }

  Future<void> vaciar() async {
    await abrir();
    _memoria.clear();
    if (_dir != null && await _dir!.exists()) {
      await _dir!.delete(recursive: true);
      await _dir!.create(recursive: true);
    }
  }
}

class SinConexion extends ChangeNotifier {
  SinConexion({Almacen? almacen}) : _almacen = almacen ?? Almacen();

  final Almacen _almacen;
  Dio? _dio;
  bool _enLinea = true;
  bool _sincronizando = false;
  List<Pendiente> _cola = [];
  final Map<String, String> _idsReales = {};
  StreamSubscription<List<ConnectivityResult>>? _red;
  Timer? _reloj;

  /// Se llama al terminar de subir cambios, para refrescar pantallas.
  VoidCallback? alSincronizar;

  bool get enLinea => _enLinea;
  bool get sincronizando => _sincronizando;
  List<Pendiente> get pendientes => _cola.where((p) => p.error == null).toList();
  List<Pendiente> get conflictos => _cola.where((p) => p.error != null).toList();

  Future<void> iniciar(Dio dio) async {
    _dio = dio;
    // El interceptor va de inmediato: la primera petición (revivir la sesión)
    // ya debe poder resolverse sin red.
    dio.interceptors.add(interceptor());
    await _almacen.abrir();
    final guardada = await _almacen.leer('cola');
    if (guardada != null) {
      try {
        _cola = [for (final p in jsonDecode(guardada) as List) Pendiente.fromJson((p as Map).cast<String, dynamic>())];
      } catch (_) {
        _cola = [];
      }
    }
    if (!kIsWeb) {
      try {
        _red = Connectivity().onConnectivityChanged.listen(
          (r) {
            if (r.any((x) => x != ConnectivityResult.none)) sincronizar();
          },
          onError: (_) {}, // sin el servicio de red del sistema, queda el reintento periódico
        );
      } catch (_) {}
    }
    // Además de avisar el sistema, se reintenta cada 30 s mientras haya cola.
    _reloj = Timer.periodic(const Duration(seconds: 30), (_) {
      if (pendientes.isNotEmpty) sincronizar();
    });
    notifyListeners();
    if (pendientes.isNotEmpty) unawaited(sincronizar());
  }

  @override
  void dispose() {
    _red?.cancel();
    _reloj?.cancel();
    super.dispose();
  }

  void _estado(bool enLinea) {
    if (_enLinea == enLinea) return;
    _enLinea = enLinea;
    notifyListeners();
    if (enLinea && pendientes.isNotEmpty) unawaited(sincronizar());
  }

  Future<void> _guardarCola() => _almacen.escribir('cola', jsonEncode([for (final p in _cola) p.toJson()]));

  static bool _faltaRed(DioException e) => switch (e.type) {
    DioExceptionType.connectionError || DioExceptionType.connectionTimeout || DioExceptionType.sendTimeout => true,
    DioExceptionType.receiveTimeout => true,
    DioExceptionType.unknown => e.error is SocketException || e.error is HttpException,
    _ => false,
  };

  static String _clave(String ruta, Map<String, dynamic> query) {
    if (query.isEmpty) return 'get:$ruta';
    final orden = query.keys.toList()..sort();
    return 'get:$ruta?${orden.map((k) => '$k=${query[k]}').join('&')}';
  }

  static bool encolable(RequestOptions o) =>
      o.method != 'GET' && o.data is! FormData && !_soloEnLinea.any((r) => o.path.contains(r));

  Interceptor interceptor() => InterceptorsWrapper(
    onRequest: (o, handler) async {
      if (o.method != 'GET') o.headers.putIfAbsent('Idempotency-Key', nuevaLlave);
      // Con cambios en cola, los nuevos van detrás para respetar el orden.
      if (o.extra['reenvio'] != true && encolable(o) && pendientes.isNotEmpty) {
        return handler.resolve(await _encolar(o));
      }
      handler.next(o);
    },
    onResponse: (r, handler) async {
      _estado(true);
      final o = r.requestOptions;
      if (o.method == 'GET' && r.statusCode == 200 && o.responseType == ResponseType.json) {
        try {
          await _almacen.escribir(_clave(o.path, o.queryParameters), jsonEncode(r.data));
        } catch (_) {}
      }
      handler.next(r);
    },
    onError: (e, handler) async {
      if (!_faltaRed(e)) return handler.next(e);
      _estado(false);
      final o = e.requestOptions;
      if (o.method == 'GET') {
        final copia = await _almacen.leer(_clave(o.path, o.queryParameters));
        if (copia != null) {
          return handler.resolve(Response(requestOptions: o, statusCode: 200, data: jsonDecode(copia), extra: {'desdeCopia': true}));
        }
        // Buscar pacientes sin red: se filtra la lista guardada.
        final busca = '${o.queryParameters['search'] ?? ''}'.trim().toLowerCase();
        if (o.path == '/patients' && busca.isNotEmpty) {
          final lista = await _listaGuardada('/patients');
          if (lista != null) {
            final hallados = lista.where((x) {
              if (x is! Map) return false;
              final texto = '${x['first_name']} ${x['last_name']} ${x['national_id'] ?? ''}'.toLowerCase();
              return busca.split(RegExp(r'\s+')).every(texto.contains);
            }).toList();
            return handler.resolve(Response(requestOptions: o, statusCode: 200, data: hallados, extra: {'desdeCopia': true}));
          }
        }
        return handler.next(e);
      }
      if (o.extra['reenvio'] != true && encolable(o)) {
        return handler.resolve(await _encolar(o));
      }
      handler.next(e);
    },
  );

  /// La lista guardada más completa de una ruta (cualquier consulta).
  Future<List<dynamic>?> _listaGuardada(String ruta) async {
    List<dynamic>? mejor;
    for (final clave in await _almacen.claves('get:$ruta')) {
      if (clave.substring(4).split('?').first != ruta) continue;
      final texto = await _almacen.leer(clave);
      if (texto == null) continue;
      final dato = jsonDecode(texto);
      final lista = dato is List ? dato : (dato is Map && dato['items'] is List ? dato['items'] as List : null);
      if (lista != null && (mejor == null || lista.length > mejor.length)) mejor = lista;
    }
    return mejor;
  }

  Future<Response<dynamic>> _encolar(RequestOptions o) async {
    final crea = o.method == 'POST' && !RegExp(r'/(status|void|cancel|archive|restore|sign|accept|items)$').hasMatch(o.path);
    final idTemporal = crea ? 'tmp-${nuevaLlave()}' : null;
    final p = Pendiente(
      id: '${o.headers['Idempotency-Key']}',
      metodo: o.method,
      ruta: o.path,
      datos: o.data,
      query: o.queryParameters.isEmpty ? null : o.queryParameters,
      creado: DateTime.now(),
      idTemporal: idTemporal,
    );
    _cola.add(p);
    await _guardarCola();
    final optimista = await _aplicarEnCopia(p);
    notifyListeners();
    return Response(requestOptions: o, statusCode: 202, data: optimista, extra: {'encolado': true});
  }

  /// Refleja el cambio en las copias guardadas, para verlo ya en pantalla.
  Future<dynamic> _aplicarEnCopia(Pendiente p) async {
    final datos = p.datos is Map ? Map<String, dynamic>.from(p.datos as Map) : <String, dynamic>{};
    final partes = p.ruta.split('/').where((x) => x.isNotEmpty).toList();
    final padre = '/${partes.take(partes.length - 1).join('/')}';
    final id = partes.isEmpty ? '' : partes.last;

    Future<void> editarListas(String rutaLista, String idElemento, Map<String, dynamic> cambios, {bool quitar = false}) async {
      for (final clave in await _almacen.claves('get:$rutaLista')) {
        final base = clave.substring(4).split('?').first;
        if (base != rutaLista) continue;
        final texto = await _almacen.leer(clave);
        if (texto == null) continue;
        final dato = jsonDecode(texto);
        final lista = dato is List ? dato : (dato is Map && dato['items'] is List ? dato['items'] as List : null);
        if (lista == null) continue;
        if (quitar) {
          lista.removeWhere((x) => x is Map && '${x['id']}' == idElemento);
        } else {
          for (final x in lista) {
            if (x is Map && '${x['id']}' == idElemento) x.addAll(cambios);
          }
        }
        await _almacen.escribir(clave, jsonEncode(dato));
      }
    }

    const acciones = {'status', 'void', 'cancel', 'archive', 'restore', 'sign', 'accept'};
    final esAccion = acciones.contains(id);
    switch (p.metodo) {
      case 'POST' when p.idTemporal != null:
        final nuevo = {...datos, 'id': p.idTemporal, '_pendiente': true};
        for (final clave in await _almacen.claves('get:${p.ruta}')) {
          if (clave.substring(4).split('?').first != p.ruta) continue;
          final texto = await _almacen.leer(clave);
          if (texto == null) continue;
          final dato = jsonDecode(texto);
          if (dato is List) {
            dato.insert(0, nuevo);
          } else if (dato is Map && dato['items'] is List) {
            (dato['items'] as List).insert(0, nuevo);
          } else {
            continue;
          }
          await _almacen.escribir(clave, jsonEncode(dato));
        }
        return nuevo;
      case 'POST' || 'PUT' || 'PATCH' when esAccion:
        // Acciones sobre un recurso (cambiar estado, anular…): se marca en él.
        final recurso = padre;
        final segs = recurso.split('/').where((x) => x.isNotEmpty).toList();
        final cambios = {...datos, '_pendiente': true};
        if (id == 'status' && datos['status'] != null) cambios['status'] = datos['status'];
        if (id == 'void') cambios['voided_at'] = DateTime.now().toUtc().toIso8601String();
        final copia = await _almacen.leer('get:$recurso');
        if (copia != null) {
          final dato = jsonDecode(copia);
          if (dato is Map) await _almacen.escribir('get:$recurso', jsonEncode({...dato, ...cambios}));
        }
        if (segs.length >= 2) await editarListas('/${segs.take(segs.length - 1).join('/')}', segs.last, cambios);
        return {...cambios, 'id': segs.isEmpty ? null : segs.last};
      case 'PUT' || 'PATCH':
        final copia = await _almacen.leer('get:${p.ruta}');
        Map<String, dynamic> resultado = {...datos, 'id': id, '_pendiente': true};
        if (copia != null) {
          final dato = jsonDecode(copia);
          if (dato is Map) {
            resultado = {...dato.cast<String, dynamic>(), ...datos, '_pendiente': true};
            await _almacen.escribir('get:${p.ruta}', jsonEncode(resultado));
          }
        }
        await editarListas(padre, id, {...datos, '_pendiente': true});
        return resultado;
      case 'DELETE':
        await _almacen.borrar('get:${p.ruta}');
        await editarListas(padre, id, const {}, quitar: true);
        return null;
    }
    return datos;
  }

  String _conIdsReales(String texto) {
    var t = texto;
    _idsReales.forEach((tmp, real) => t = t.replaceAll(tmp, real));
    return t;
  }

  /// Sube la cola en orden. Se detiene al primer corte de red; un rechazo
  /// del servidor (dato inválido, ya anulado…) queda como conflicto para que
  /// la persona decida, sin frenar lo demás.
  Future<void> sincronizar() async {
    final dio = _dio;
    if (dio == null || _sincronizando || pendientes.isEmpty) return;
    _sincronizando = true;
    notifyListeners();
    var subidos = 0;
    try {
      for (final p in List.of(pendientes)) {
        // Un cambio sobre algo creado sin conexión usa ya el id real.
        p.ruta = _conIdsReales(p.ruta);
        if (p.datos != null) p.datos = jsonDecode(_conIdsReales(jsonEncode(p.datos)));
        if (p.ruta.contains('tmp-')) {
          p.error = 'Depende de un registro que no se pudo subir.';
          continue;
        }
        try {
          final r = await dio.request<dynamic>(
            p.ruta,
            data: p.datos,
            queryParameters: p.query,
            options: Options(method: p.metodo, headers: {'Idempotency-Key': p.id}, extra: {'reenvio': true}),
          );
          final code = r.statusCode ?? 0;
          if (code >= 200 && code < 300) {
            if (p.idTemporal != null && r.data is Map && r.data['id'] != null) {
              _idsReales[p.idTemporal!] = '${r.data['id']}';
            }
            _cola.remove(p);
            subidos++;
          } else if (code == 401) {
            break; // sesión vencida: se reintenta tras volver a entrar
          } else {
            p.error = (r.data is Map && r.data['detail'] is String) ? r.data['detail'] as String : 'El servidor lo rechazó ($code).';
          }
        } on DioException catch (e) {
          if (_faltaRed(e)) {
            _estado(false);
            break;
          }
          p.error = 'No se pudo subir: ${e.message ?? e.type.name}';
        }
        await _guardarCola();
      }
    } finally {
      _sincronizando = false;
      await _guardarCola();
      notifyListeners();
      if (subidos > 0) alSincronizar?.call();
    }
  }

  Future<void> descartar(Pendiente p) async {
    _cola.remove(p);
    await _guardarCola();
    notifyListeners();
  }

  Future<void> reintentar(Pendiente p) async {
    p.error = null;
    await _guardarCola();
    notifyListeners();
    await sincronizar();
  }

  /// Al cerrar sesión: nada de esta persona queda en el teléfono.
  Future<void> olvidarTodo() async {
    _cola.clear();
    _idsReales.clear();
    await _almacen.vaciar();
    notifyListeners();
  }

  // Usuario de la última sesión, para entrar sin red.
  Future<void> guardarUsuario(Map<String, dynamic> datos) => _almacen.escribir('usuario', jsonEncode(datos));

  Future<Map<String, dynamic>?> usuarioGuardado() async {
    final t = await _almacen.leer('usuario');
    return t == null ? null : (jsonDecode(t) as Map).cast<String, dynamic>();
  }
}
