import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:odonto_movil/core/offline/sin_conexion.dart';

/// Servidor simulado: responde lo de [datos] y, con [caido], no contesta.
class _Servidor implements HttpClientAdapter {
  bool caido = false;
  final Map<String, dynamic> datos = {};
  final List<RequestOptions> recibidas = [];
  int _ids = 0;
  final Map<String, int> rechazos = {};

  @override
  Future<ResponseBody> fetch(RequestOptions o, Stream<Uint8List>? s, Future<void>? c) async {
    if (caido) {
      throw DioException.connectionError(requestOptions: o, reason: 'sin red', error: const SocketException('sin red'));
    }
    recibidas.add(o);
    if (rechazos.containsKey(o.path)) {
      return ResponseBody.fromString(jsonEncode({'detail': 'Dato inválido'}), rechazos[o.path]!, headers: {Headers.contentTypeHeader: [Headers.jsonContentType]});
    }
    dynamic cuerpo;
    var codigo = 200;
    if (o.method == 'GET') {
      cuerpo = datos[o.path];
      if (cuerpo == null) codigo = 404;
    } else if (o.method == 'POST') {
      cuerpo = {...(o.data as Map? ?? {}), 'id': 'real${++_ids}'};
      codigo = 201;
    } else {
      cuerpo = {...(o.data as Map? ?? {}), 'id': o.path.split('/').last};
    }
    return ResponseBody.fromString(jsonEncode(cuerpo), codigo, headers: {Headers.contentTypeHeader: [Headers.jsonContentType]});
  }

  @override
  void close({bool force = false}) {}
}

Future<(Dio, _Servidor, SinConexion)> _preparar() async {
  final servidor = _Servidor();
  final dio = Dio(BaseOptions(baseUrl: 'http://x/api/v1', validateStatus: (c) => c != null && c < 500))..httpClientAdapter = servidor;
  final sc = SinConexion();
  await sc.iniciar(dio);
  return (dio, servidor, sc);
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('sin red muestra la copia guardada y la búsqueda filtra en el teléfono', () async {
    final (dio, srv, sc) = await _preparar();
    srv.datos['/patients'] = [
      {'id': 'p1', 'first_name': 'Lucía', 'last_name': 'Arce', 'national_id': '1710034065'},
      {'id': 'p2', 'first_name': 'Mario', 'last_name': 'Paz', 'national_id': '0912345678'},
    ];
    expect((await dio.get('/patients')).data, hasLength(2));
    srv.caido = true;
    final r = await dio.get('/patients');
    expect(r.data, hasLength(2));
    expect(r.extra['desdeCopia'], isTrue);
    expect(sc.enLinea, isFalse);
    final busqueda = await dio.get('/patients', queryParameters: {'search': 'arce'});
    expect((busqueda.data as List).single['id'], 'p1');
    sc.dispose();
  });

  test('editar sin red se ve al instante y se sube al volver, con su llave', () async {
    final (dio, srv, sc) = await _preparar();
    srv.datos['/patients/p1'] = {'id': 'p1', 'first_name': 'Lucía', 'phone': '099'};
    srv.datos['/patients'] = [{'id': 'p1', 'first_name': 'Lucía', 'phone': '099'}];
    await dio.get('/patients/p1');
    await dio.get('/patients');

    srv.caido = true;
    final r = await dio.put('/patients/p1', data: {'phone': '0988888888'});
    expect(r.statusCode, 202);
    expect(sc.pendientes, hasLength(1));
    expect((await dio.get('/patients/p1')).data['phone'], '0988888888');
    expect(((await dio.get('/patients')).data as List).first['phone'], '0988888888');

    srv.caido = false;
    await sc.sincronizar();
    expect(sc.pendientes, isEmpty);
    final put = srv.recibidas.lastWhere((o) => o.method == 'PUT');
    expect(put.path, '/patients/p1');
    expect(put.headers['Idempotency-Key'], isNotEmpty);
    expect(put.data, {'phone': '0988888888'});
    sc.dispose();
  });

  test('lo creado sin red y lo que depende de ello se sube con el id real', () async {
    final (dio, srv, sc) = await _preparar();
    srv.datos['/patients'] = <dynamic>[];
    await dio.get('/patients');
    srv.caido = true;
    final creado = await dio.post('/patients', data: {'first_name': 'Rosa', 'last_name': 'Nueva'});
    final tmp = creado.data['id'] as String;
    expect(tmp, startsWith('tmp-'));
    expect(((await dio.get('/patients')).data as List).first['first_name'], 'Rosa');
    await dio.post('/patients/$tmp/evolutions', data: {'procedure': 'Limpieza'});
    expect(sc.pendientes, hasLength(2));

    srv.caido = false;
    await sc.sincronizar();
    expect(sc.pendientes, isEmpty);
    expect(srv.recibidas.where((o) => o.method == 'POST').map((o) => o.path), ['/patients', '/patients/real1/evolutions']);
    sc.dispose();
  });

  test('un rechazo del servidor queda como conflicto y no frena lo demás', () async {
    final (dio, srv, sc) = await _preparar();
    srv.caido = true;
    await dio.put('/patients/p1', data: {'email': 'malo'});
    await dio.put('/patients/p2', data: {'phone': '099'});
    srv.caido = false;
    srv.rechazos['/patients/p1'] = 422;
    await sc.sincronizar();
    expect(sc.conflictos.single.error, 'Dato inválido');
    expect(sc.pendientes, isEmpty);
    expect(srv.recibidas.any((o) => o.path == '/patients/p2'), isTrue);
    await sc.descartar(sc.conflictos.single);
    expect(sc.conflictos, isEmpty);
    sc.dispose();
  });

  test('facturar no se encola: necesita al SRI en ese momento', () async {
    final (dio, srv, sc) = await _preparar();
    srv.caido = true;
    expect(() => dio.post('/invoices', data: {'items': []}), throwsA(isA<DioException>()));
    expect(sc.pendientes, isEmpty);
    sc.dispose();
  });
}
