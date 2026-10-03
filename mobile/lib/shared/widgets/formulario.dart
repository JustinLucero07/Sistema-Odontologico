import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/api/repositorios.dart';
import 'glass.dart';

/// Tipos de campo del formulario emergente.
enum TipoCampo {
  texto,
  multilinea,
  numero,
  entero,
  dinero,
  fecha,
  hora,
  seleccion,
  interruptor,
  telefono,
  correo,
  buscar,
}

typedef Opcion = (String codigo, String etiqueta);

/// Un campo del formulario. Se describe con datos y el formulario lo dibuja:
/// así todas las altas y ediciones de la app se ven y se comportan igual.
class Campo {
  const Campo(
    this.clave,
    this.etiqueta, {
    this.tipo = TipoCampo.texto,
    this.requerido = false,
    this.inicial,
    this.inicialEtiqueta,
    this.opciones = const [],
    this.ayuda,
    this.icono,
    this.buscar,
    this.mitad = false,
    this.seccion,
  });

  final String clave;
  final String etiqueta;
  final TipoCampo tipo;
  final bool requerido;
  final dynamic inicial;

  /// Para [TipoCampo.buscar]: el texto que se muestra del valor inicial.
  final String? inicialEtiqueta;
  final List<Opcion> opciones;
  final String? ayuda;
  final IconData? icono;

  /// Para [TipoCampo.buscar]: devuelve las coincidencias de lo que se escribe.
  final Future<List<Opcion>> Function(String texto)? buscar;

  /// Ocupa media fila (dos campos lado a lado).
  final bool mitad;

  /// Título de sección que aparece encima de este campo.
  final String? seccion;
}

/// Formulario en hoja emergente de vidrio. Valida, muestra el error del
/// servidor dentro de la hoja (sin cerrarla ni perder lo escrito) y se cierra
/// solo cuando [alGuardar] termina bien. Devuelve los valores guardados.
Future<Map<String, dynamic>?> mostrarFormulario(
  BuildContext context, {
  required String titulo,
  String? subtitulo,
  IconData icono = Icons.edit_outlined,
  required List<Campo> campos,
  String textoGuardar = 'Guardar',
  bool peligro = false,
  required Future<void> Function(Map<String, dynamic> valores) alGuardar,
}) {
  return showModalBottomSheet<Map<String, dynamic>>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    backgroundColor: Colors.transparent,
    builder: (_) => _HojaFormulario(
      titulo: titulo,
      subtitulo: subtitulo,
      icono: icono,
      campos: campos,
      textoGuardar: textoGuardar,
      peligro: peligro,
      alGuardar: alGuardar,
    ),
  );
}

class _HojaFormulario extends StatefulWidget {
  const _HojaFormulario({
    required this.titulo,
    required this.subtitulo,
    required this.icono,
    required this.campos,
    required this.textoGuardar,
    required this.peligro,
    required this.alGuardar,
  });

  final String titulo;
  final String? subtitulo;
  final IconData icono;
  final List<Campo> campos;
  final String textoGuardar;
  final bool peligro;
  final Future<void> Function(Map<String, dynamic>) alGuardar;

  @override
  State<_HojaFormulario> createState() => _HojaFormularioState();
}

class _HojaFormularioState extends State<_HojaFormulario> {
  final _form = GlobalKey<FormState>();
  final _textos = <String, TextEditingController>{};
  final _valores = <String, dynamic>{};
  final _etiquetas = <String, String>{};
  bool _guardando = false;
  String? _error;

  static bool _esTexto(TipoCampo t) => const {
    TipoCampo.texto,
    TipoCampo.multilinea,
    TipoCampo.numero,
    TipoCampo.entero,
    TipoCampo.dinero,
    TipoCampo.telefono,
    TipoCampo.correo,
  }.contains(t);

  @override
  void initState() {
    super.initState();
    for (final c in widget.campos) {
      if (_esTexto(c.tipo)) {
        _textos[c.clave] = TextEditingController(
          text: c.inicial == null ? '' : '${c.inicial}',
        );
      } else if (c.tipo == TipoCampo.interruptor) {
        _valores[c.clave] = c.inicial == true;
      } else if (c.tipo == TipoCampo.seleccion) {
        final existe = c.opciones.any((o) => o.$1 == c.inicial);
        _valores[c.clave] = existe
            ? c.inicial
            : (c.requerido && c.opciones.isNotEmpty
                  ? c.opciones.first.$1
                  : null);
      } else {
        _valores[c.clave] = c.inicial;
        if (c.inicialEtiqueta != null) {
          _etiquetas[c.clave] = c.inicialEtiqueta!;
        }
      }
    }
  }

  @override
  void dispose() {
    for (final t in _textos.values) {
      t.dispose();
    }
    super.dispose();
  }

  Map<String, dynamic> _recoger() {
    final salida = <String, dynamic>{};
    for (final c in widget.campos) {
      if (_esTexto(c.tipo)) {
        final t = _textos[c.clave]!.text.trim();
        salida[c.clave] = switch (c.tipo) {
          _ when t.isEmpty => null,
          TipoCampo.dinero || TipoCampo.numero => t.replaceAll(',', '.'),
          TipoCampo.entero => int.tryParse(t),
          _ => t,
        };
      } else {
        salida[c.clave] = _valores[c.clave];
      }
    }
    return salida;
  }

  Future<void> _guardar() async {
    if (!(_form.currentState?.validate() ?? false)) return;
    for (final c in widget.campos) {
      if (c.requerido && !_esTexto(c.tipo) && _valores[c.clave] == null) {
        setState(() => _error = 'Complete «${c.etiqueta}».');
        return;
      }
    }
    setState(() {
      _guardando = true;
      _error = null;
    });
    final valores = _recoger();
    try {
      await widget.alGuardar(valores);
      if (mounted) Navigator.of(context).pop(valores);
    } on ErrorApi catch (e) {
      if (mounted) setState(() => _error = e.mensaje);
    } catch (_) {
      if (mounted) setState(() => _error = 'No se pudo guardar.');
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final dark = Theme.of(context).brightness == Brightness.dark;
    final teclado = MediaQuery.viewInsetsOf(context).bottom;

    // Empareja los campos de media fila.
    final filas = <Widget>[];
    for (var i = 0; i < widget.campos.length; i++) {
      final c = widget.campos[i];
      if (c.seccion != null) {
        filas.add(
          Padding(
            padding: EdgeInsets.only(top: filas.isEmpty ? 0 : 10, bottom: 8),
            child: Text(
              c.seccion!.toUpperCase(),
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.9,
                color: scheme.onSurface.withValues(alpha: 0.45),
              ),
            ),
          ),
        );
      }
      final siguiente = i + 1 < widget.campos.length
          ? widget.campos[i + 1]
          : null;
      if (c.mitad &&
          siguiente != null &&
          siguiente.mitad &&
          siguiente.seccion == null) {
        filas.add(
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(child: _campo(c)),
                const SizedBox(width: 10),
                Expanded(child: _campo(siguiente)),
              ],
            ),
          ),
        );
        i++;
      } else {
        filas.add(
          Padding(padding: const EdgeInsets.only(bottom: 12), child: _campo(c)),
        );
      }
    }

    return Padding(
      padding: EdgeInsets.only(bottom: teclado),
      child: Container(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.sizeOf(context).height * 0.92,
        ),
        decoration: BoxDecoration(
          color: dark ? const Color(0xF2122427) : const Color(0xF7F6FAF9),
          borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
          border: Border.all(
            color: dark
                ? Colors.white.withValues(alpha: 0.08)
                : Colors.white.withValues(alpha: 0.9),
          ),
        ),
        child: Form(
          key: _form,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const SizedBox(height: 10),
              Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: scheme.onSurface.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 14, 12, 8),
                child: Row(
                  children: [
                    Container(
                      width: 42,
                      height: 42,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(14),
                        color: (widget.peligro ? scheme.error : scheme.primary)
                            .withValues(alpha: 0.13),
                      ),
                      child: Icon(
                        widget.icono,
                        color: widget.peligro ? scheme.error : scheme.primary,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            widget.titulo,
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w700,
                              letterSpacing: -0.3,
                            ),
                          ),
                          if (widget.subtitulo != null)
                            Text(
                              widget.subtitulo!,
                              style: TextStyle(
                                fontSize: 12.5,
                                color: scheme.onSurface.withValues(alpha: 0.55),
                              ),
                            ),
                        ],
                      ),
                    ),
                    IconButton(
                      tooltip: 'Cerrar',
                      onPressed: () => Navigator.of(context).pop(),
                      icon: const Icon(Icons.close),
                    ),
                  ],
                ),
              ),
              Flexible(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(20, 8, 20, 8),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: filas,
                  ),
                ),
              ),
              if (_error != null)
                Container(
                  margin: const EdgeInsets.fromLTRB(20, 0, 20, 8),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: scheme.error.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.error_outline, color: scheme.error, size: 20),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _error!,
                          style: TextStyle(color: scheme.error, fontSize: 13),
                        ),
                      ),
                    ],
                  ),
                ),
              Container(
                padding: EdgeInsets.fromLTRB(
                  20,
                  12,
                  20,
                  12 + MediaQuery.paddingOf(context).bottom,
                ),
                decoration: BoxDecoration(
                  border: Border(
                    top: BorderSide(
                      color: scheme.onSurface.withValues(alpha: 0.08),
                    ),
                  ),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: _guardando
                            ? null
                            : () => Navigator.of(context).pop(),
                        style: OutlinedButton.styleFrom(
                          minimumSize: const Size.fromHeight(50),
                          shape: const StadiumBorder(),
                        ),
                        child: const Text('Cancelar'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      flex: 2,
                      child: FilledButton(
                        onPressed: _guardando ? null : _guardar,
                        style: widget.peligro
                            ? FilledButton.styleFrom(
                                backgroundColor: scheme.error,
                                foregroundColor: scheme.onError,
                              )
                            : null,
                        child: _guardando
                            ? const SizedBox(
                                width: 22,
                                height: 22,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2.4,
                                ),
                              )
                            : Text(widget.textoGuardar),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _campo(Campo c) {
    final decoracion = InputDecoration(
      labelText: c.requerido ? '${c.etiqueta} *' : c.etiqueta,
      helperText: c.ayuda,
      helperMaxLines: 2,
      prefixIcon: c.icono == null ? null : Icon(c.icono, size: 20),
      prefixText: c.tipo == TipoCampo.dinero ? '\$ ' : null,
    );

    switch (c.tipo) {
      case TipoCampo.interruptor:
        return SwitchListTile(
          value: _valores[c.clave] as bool? ?? false,
          onChanged: (v) => setState(() => _valores[c.clave] = v),
          title: Text(c.etiqueta),
          subtitle: c.ayuda == null ? null : Text(c.ayuda!),
          contentPadding: EdgeInsets.zero,
        );
      case TipoCampo.seleccion:
        return DropdownButtonFormField<String>(
          initialValue: _valores[c.clave] as String?,
          isExpanded: true,
          decoration: decoracion,
          items: [
            if (!c.requerido)
              const DropdownMenuItem<String>(value: null, child: Text('—')),
            for (final o in c.opciones)
              DropdownMenuItem(
                value: o.$1,
                child: Text(o.$2, overflow: TextOverflow.ellipsis),
              ),
          ],
          onChanged: (v) => setState(() => _valores[c.clave] = v),
          validator: (v) => c.requerido && v == null ? 'Obligatorio' : null,
        );
      case TipoCampo.fecha:
      case TipoCampo.hora:
      case TipoCampo.buscar:
        final valor = _valores[c.clave];
        final texto = switch (c.tipo) {
          _ when valor == null => '',
          TipoCampo.fecha => DateFormat(
            'dd/MM/yyyy',
          ).format(DateTime.parse('$valor')),
          TipoCampo.hora => '$valor',
          _ => _etiquetas[c.clave] ?? '$valor',
        };
        return InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: () => _elegir(c),
          child: InputDecorator(
            isEmpty: texto.isEmpty,
            decoration: decoracion.copyWith(
              suffixIcon: Icon(switch (c.tipo) {
                TipoCampo.fecha => Icons.calendar_today_outlined,
                TipoCampo.hora => Icons.schedule,
                _ => Icons.search,
              }, size: 20),
            ),
            child: Text(texto, overflow: TextOverflow.ellipsis),
          ),
        );
      default:
        final numerico = const {
          TipoCampo.numero,
          TipoCampo.entero,
          TipoCampo.dinero,
        }.contains(c.tipo);
        return TextFormField(
          controller: _textos[c.clave],
          decoration: decoracion,
          maxLines: c.tipo == TipoCampo.multilinea ? 4 : 1,
          minLines: c.tipo == TipoCampo.multilinea ? 2 : 1,
          keyboardType: switch (c.tipo) {
            TipoCampo.numero || TipoCampo.dinero =>
              const TextInputType.numberWithOptions(decimal: true),
            TipoCampo.entero => TextInputType.number,
            TipoCampo.telefono => TextInputType.phone,
            TipoCampo.correo => TextInputType.emailAddress,
            TipoCampo.multilinea => TextInputType.multiline,
            _ => TextInputType.text,
          },
          textCapitalization:
              c.tipo == TipoCampo.texto || c.tipo == TipoCampo.multilinea
              ? TextCapitalization.sentences
              : TextCapitalization.none,
          autocorrect: c.tipo != TipoCampo.correo,
          validator: (v) {
            final t = (v ?? '').trim();
            if (t.isEmpty) return c.requerido ? 'Obligatorio' : null;
            if (numerico && double.tryParse(t.replaceAll(',', '.')) == null) {
              return 'Escriba un número';
            }
            if (c.tipo == TipoCampo.correo && !t.contains('@')) {
              return 'Correo no válido';
            }
            return null;
          },
        );
    }
  }

  Future<void> _elegir(Campo c) async {
    final actual = _valores[c.clave];
    switch (c.tipo) {
      case TipoCampo.fecha:
        final hoy = DateTime.now();
        final elegido = await showDatePicker(
          context: context,
          initialDate: actual == null ? hoy : DateTime.parse('$actual'),
          firstDate: DateTime(hoy.year - 110),
          lastDate: DateTime(hoy.year + 5),
        );
        if (elegido != null) {
          setState(
            () => _valores[c.clave] = DateFormat('yyyy-MM-dd').format(elegido),
          );
        }
      case TipoCampo.hora:
        final partes = '${actual ?? '09:00'}'.split(':');
        final elegido = await showTimePicker(
          context: context,
          initialTime: TimeOfDay(
            hour: int.tryParse(partes[0]) ?? 9,
            minute: int.tryParse(partes.length > 1 ? partes[1] : '0') ?? 0,
          ),
        );
        if (elegido != null) {
          setState(
            () => _valores[c.clave] =
                '${elegido.hour.toString().padLeft(2, '0')}:${elegido.minute.toString().padLeft(2, '0')}',
          );
        }
      case TipoCampo.buscar:
        final elegido = await elegirConBusqueda(
          context,
          titulo: c.etiqueta,
          buscar: c.buscar!,
        );
        if (elegido != null) {
          setState(() {
            _valores[c.clave] = elegido.$1;
            _etiquetas[c.clave] = elegido.$2;
          });
        }
      default:
        break;
    }
  }
}

/// Buscador emergente: escribe y elige (pacientes, artículos…).
Future<Opcion?> elegirConBusqueda(
  BuildContext context, {
  required String titulo,
  required Future<List<Opcion>> Function(String texto) buscar,
}) {
  return showModalBottomSheet<Opcion>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    showDragHandle: true,
    builder: (_) => _Buscador(titulo: titulo, buscar: buscar),
  );
}

class _Buscador extends StatefulWidget {
  const _Buscador({required this.titulo, required this.buscar});

  final String titulo;
  final Future<List<Opcion>> Function(String) buscar;

  @override
  State<_Buscador> createState() => _BuscadorState();
}

class _BuscadorState extends State<_Buscador> {
  Timer? _espera;
  List<Opcion> _resultados = [];
  bool _cargando = true;

  @override
  void initState() {
    super.initState();
    _consultar('');
  }

  @override
  void dispose() {
    _espera?.cancel();
    super.dispose();
  }

  Future<void> _consultar(String texto) async {
    setState(() => _cargando = true);
    try {
      final r = await widget.buscar(texto);
      if (mounted) setState(() => _resultados = r);
    } catch (_) {
      if (mounted) setState(() => _resultados = []);
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SizedBox(
        height: MediaQuery.sizeOf(context).height * 0.7,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
              child: TextField(
                autofocus: true,
                decoration: InputDecoration(
                  hintText: 'Buscar ${widget.titulo.toLowerCase()}',
                  prefixIcon: const Icon(Icons.search),
                ),
                onChanged: (t) {
                  _espera?.cancel();
                  _espera = Timer(
                    const Duration(milliseconds: 300),
                    () => _consultar(t),
                  );
                },
              ),
            ),
            if (_cargando) const LinearProgressIndicator(minHeight: 2),
            Expanded(
              child: _resultados.isEmpty && !_cargando
                  ? const Center(child: Text('Sin resultados'))
                  : ListView.builder(
                      itemCount: _resultados.length,
                      itemBuilder: (context, i) {
                        final o = _resultados[i];
                        return ListTile(
                          leading: const Icon(Icons.chevron_right),
                          title: Text(o.$2),
                          onTap: () => Navigator.of(context).pop(o),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Pregunta de confirmación (sí / no) en el mismo estilo.
Future<bool> confirmar(
  BuildContext context, {
  required String titulo,
  String? mensaje,
  String textoConfirmar = 'Confirmar',
  bool peligro = false,
}) async {
  final scheme = Theme.of(context).colorScheme;
  final r = await showDialog<bool>(
    context: context,
    builder: (_) => AlertDialog(
      title: Text(titulo),
      content: mensaje == null ? null : Text(mensaje),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, false),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          style: FilledButton.styleFrom(
            minimumSize: const Size(100, 44),
            backgroundColor: peligro ? scheme.error : null,
            foregroundColor: peligro ? scheme.onError : null,
          ),
          onPressed: () => Navigator.pop(context, true),
          child: Text(textoConfirmar),
        ),
      ],
    ),
  );
  return r ?? false;
}

/// Anular algo pide siempre el motivo: no se borra, queda registrado.
Future<void> anularConMotivo(
  BuildContext context, {
  required String que,
  required Future<void> Function(String motivo) alAnular,
}) async {
  await mostrarFormulario(
    context,
    titulo: 'Anular $que',
    subtitulo: 'No se borra: queda registrado con su motivo.',
    icono: Icons.block,
    peligro: true,
    textoGuardar: 'Anular',
    campos: const [
      Campo('reason', 'Motivo', tipo: TipoCampo.multilinea, requerido: true),
    ],
    alGuardar: (v) => alAnular(v['reason'] as String),
  );
}

/// Carga lo que necesita un formulario antes de abrirse; si falla (sin red,
/// sin permiso) lo dice en vez de quedarse sin responder.
Future<T?> cargarOAvisar<T>(BuildContext context, Future<T> futuro) async {
  try {
    return await futuro;
  } on ErrorApi catch (e) {
    if (context.mounted) avisar(context, e.mensaje);
  } catch (_) {
    if (context.mounted) avisar(context, 'No se pudieron cargar los datos.');
  }
  return null;
}

/// Aviso breve abajo.
void avisar(BuildContext context, String mensaje) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(mensaje)));
}

/// Ejecuta una acción mostrando el error del servidor si falla.
Future<bool> intentar(
  BuildContext context,
  Future<void> Function() accion, {
  String? exito,
}) async {
  try {
    await accion();
    if (exito != null && context.mounted) avisar(context, exito);
    return true;
  } on ErrorApi catch (e) {
    if (context.mounted) avisar(context, e.mensaje);
  } catch (_) {
    if (context.mounted) avisar(context, 'No se pudo completar la operación.');
  }
  return false;
}

/// Fondo de página de módulo con barra de vidrio, igual en todas.
class PaginaModulo extends StatelessWidget {
  const PaginaModulo({
    super.key,
    required this.titulo,
    required this.cuerpo,
    this.accion,
    this.acciones,
    this.inferior,
  });

  final String titulo;
  final Widget cuerpo;

  /// Botón flotante (normalmente «Nuevo…»).
  final Widget? accion;
  final List<Widget>? acciones;
  final PreferredSizeWidget? inferior;

  @override
  Widget build(BuildContext context) {
    return AmbientBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          flexibleSpace: const GlassAppBarBackground(),
          title: Text(titulo),
          actions: acciones,
          bottom: inferior,
        ),
        body: cuerpo,
        floatingActionButton: accion,
      ),
    );
  }
}
