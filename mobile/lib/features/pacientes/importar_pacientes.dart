import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api.dart';
import '../../core/api/repositorios.dart';
import '../../shared/widgets/estado_vacio.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';

Future<bool> importarPacientes(BuildContext context) async {
  final elegidos = await FilePicker.pickFiles(type: FileType.custom, allowedExtensions: const ['xlsx', 'csv']);
  if (elegidos.isEmpty || !context.mounted) return false;
  final archivo = elegidos.single;
  final bytes = await archivo.readAsBytes();
  if (!context.mounted) return false;
  final r = await Navigator.of(context).push<bool>(
    MaterialPageRoute(builder: (_) => ImportarPacientesPage(nombre: archivo.name, bytes: bytes)),
  );
  return r == true;
}

class ImportarPacientesPage extends ConsumerStatefulWidget {
  const ImportarPacientesPage({super.key, required this.nombre, required this.bytes});

  final String nombre;
  final List<int> bytes;

  @override
  ConsumerState<ImportarPacientesPage> createState() => _ImportarPacientesPageState();
}

class _ImportarPacientesPageState extends ConsumerState<ImportarPacientesPage> {
  String _orden = 'nombres_apellidos';
  Map<String, dynamic>? _vista;
  Map<String, String?> _mapa = {};
  bool _cargando = true;
  bool _guardando = false;
  bool _incluirRepetidos = false;
  String _filtro = 'todos';
  String? _error;

  @override
  void initState() {
    super.initState();
    _leer();
  }

  Future<void> _leer({bool conMapa = false}) async {
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      final form = FormData.fromMap({
        'file': MultipartFile.fromBytes(widget.bytes, filename: widget.nombre),
        'name_order': _orden,
        if (conMapa) 'mapping': jsonEncode(_mapa),
      });
      final v = (await ref.read(apiProvider).post('/patients/import/preview', form) as Map).cast<String, dynamic>();
      setState(() {
        _vista = v;
        _mapa = (v['mapping'] as Map).map((k, val) => MapEntry('$k', val as String?));
      });
    } on ErrorApi catch (e) {
      setState(() => _error = e.mensaje);
    } catch (_) {
      setState(() => _error = 'No se pudo leer el archivo.');
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  List<Map<String, dynamic>> get _filas => ((_vista?['rows'] as List?) ?? []).cast<Map<String, dynamic>>();

  List<Map<String, dynamic>> get _aImportar =>
      _filas.where((r) => r['status'] == 'nuevo' || (_incluirRepetidos && r['status'] == 'duplicado')).toList();

  Future<void> _importar() async {
    setState(() => _guardando = true);
    try {
      final r = (await ref.read(apiProvider).post('/patients/import', {
        'patients': [for (final f in _aImportar) f['data']],
        'skip_duplicates': !_incluirRepetidos,
      }) as Map);
      if (!mounted) return;
      avisar(context, 'Se importaron ${r['created']} paciente(s)${(r['skipped'] ?? 0) > 0 ? ' · ${r['skipped']} ya existían' : ''}.');
      Navigator.of(context).pop(true);
    } on ErrorApi catch (e) {
      if (mounted) avisar(context, e.mensaje);
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  Color _color(String? s) => switch (s) {
    'nuevo' => Tonos.verde,
    'duplicado' => Tonos.ambar,
    _ => Tonos.rojo,
  };

  @override
  Widget build(BuildContext context) {
    final v = _vista;
    final cuentas = (v?['counts'] as Map?) ?? {};
    final campos = <(String, String)>[
      for (final f in ((v?['fields'] as List?) ?? [])) ('${f['code']}', '${f['label']}'),
    ];
    final visibles = _filtro == 'todos' ? _filas : _filas.where((r) => r['status'] == _filtro).toList();
    final n = _aImportar.length;

    return PaginaModulo(
      titulo: 'Importar pacientes',
      cuerpo: Column(
        children: [
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                GlassCard(
                  child: ListTile(
                    leading: const Icon(Icons.description_outlined),
                    title: Text(widget.nombre, style: const TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: const Text('Vista previa: nada se guarda hasta confirmar.'),
                  ),
                ),
                const SizedBox(height: 10),
                DropdownButtonFormField<String>(
                  initialValue: _orden,
                  isExpanded: true,
                  decoration: const InputDecoration(labelText: 'Si el nombre viene en una sola columna'),
                  items: const [
                    DropdownMenuItem(value: 'nombres_apellidos', child: Text('Nombres y luego apellidos')),
                    DropdownMenuItem(value: 'apellidos_nombres', child: Text('Apellidos y luego nombres')),
                  ],
                  onChanged: (o) {
                    if (o == null) return;
                    _orden = o;
                    _leer(conMapa: true);
                  },
                ),
                const SizedBox(height: 12),
                if (_cargando)
                  const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator()))
                else if (_error != null)
                  EstadoError(mensaje: _error!, onReintentar: _leer)
                else if (v != null) ...[
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: [
                        for (final (c, t) in [
                          ('todos', 'Todos ${_filas.length}'),
                          ('nuevo', 'Nuevos ${cuentas['nuevo'] ?? 0}'),
                          ('duplicado', 'Ya existen ${cuentas['duplicado'] ?? 0}'),
                          ('error', 'Con errores ${cuentas['error'] ?? 0}'),
                        ])
                          Padding(
                            padding: const EdgeInsets.only(right: 8),
                            child: ChoiceChip(
                              label: Text(t),
                              selected: _filtro == c,
                              onSelected: (_) => setState(() => _filtro = c),
                            ),
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 8),
                  GlassCard(
                    child: ExpansionTile(
                      title: Text(
                        'Columnas del archivo (${_mapa.values.where((x) => x != null).length} de ${_mapa.length} reconocidas)',
                        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
                      ),
                      childrenPadding: const EdgeInsets.fromLTRB(14, 0, 14, 12),
                      children: [
                        for (final h in _mapa.keys)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: DropdownButtonFormField<String?>(
                              initialValue: _mapa[h],
                              isExpanded: true,
                              decoration: InputDecoration(labelText: h, isDense: true),
                              items: [
                                const DropdownMenuItem<String?>(value: null, child: Text('No importar')),
                                for (final (c, t) in campos) DropdownMenuItem<String?>(value: c, child: Text(t)),
                              ],
                              onChanged: (campo) {
                                setState(() {
                                  if (campo != null) {
                                    for (final k in _mapa.keys.toList()) {
                                      if (_mapa[k] == campo) _mapa[k] = null;
                                    }
                                  }
                                  _mapa[h] = campo;
                                });
                                _leer(conMapa: true);
                              },
                            ),
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 8),
                  if (visibles.isEmpty)
                    const EstadoVacio(icono: Icons.filter_alt_off, titulo: 'Nada en este filtro')
                  else
                    for (final r in visibles.take(300))
                      FilaTarjeta(
                        icono: r['status'] == 'nuevo'
                            ? Icons.person_add_alt
                            : r['status'] == 'duplicado'
                            ? Icons.people_outline
                            : Icons.error_outline,
                        colorIcono: _color(r['status'] as String?),
                        titulo: '${r['data']['first_name']} ${r['data']['last_name']}'.trim(),
                        subtitulo: [
                          'Fila ${r['row']}',
                          if (r['data']['national_id'] != null) 'Cédula ${r['data']['national_id']}',
                          if (r['data']['phone'] != null) '${r['data']['phone']}',
                          if (r['duplicate'] != null) '${r['duplicate']}',
                          ...((r['errors'] as List?) ?? []).map((e) => '$e'),
                        ].join(' · '),
                        derecha: Pastilla(
                          switch (r['status']) {
                            'nuevo' => 'Nuevo',
                            'duplicado' => 'Ya existe',
                            _ => 'Error',
                          },
                          color: _color(r['status'] as String?),
                        ),
                      ),
                  if (visibles.length > 300)
                    Padding(
                      padding: const EdgeInsets.all(8),
                      child: Text('Se muestran 300 de ${visibles.length}. Se importan todas.', textAlign: TextAlign.center),
                    ),
                  if ((cuentas['duplicado'] ?? 0) > 0)
                    SwitchListTile(
                      value: _incluirRepetidos,
                      onChanged: (x) => setState(() => _incluirRepetidos = x),
                      title: Text('Importar también los ${cuentas['duplicado']} que parecen repetidos'),
                      subtitle: const Text('No recomendado'),
                    ),
                  const SizedBox(height: 80),
                ],
              ],
            ),
          ),
          if (v != null && !_cargando)
            SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
                child: SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: n == 0 || _guardando ? null : _importar,
                    icon: const Icon(Icons.upload_file),
                    label: Text(_guardando ? 'Importando…' : 'Importar $n paciente(s)'),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
