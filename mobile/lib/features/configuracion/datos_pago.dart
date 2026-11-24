import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/api/api.dart';
import '../../core/api/repositorios.dart';
import '../../core/auth/auth_controller.dart';
import '../../core/marca/marca.dart';
import '../../shared/contacto.dart';
import '../../shared/formato.dart';
import '../../shared/widgets/carga.dart';
import '../../shared/widgets/estado_vacio.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';

const _tiposCuenta = <Opcion>[('ahorros', 'Cuenta de ahorros'), ('corriente', 'Cuenta corriente'), ('otra', 'Otra')];

final cuentasPagoProvider = FutureProvider.autoDispose.family<List<Map<String, dynamic>>, bool>(
  (ref, todas) => ref.watch(apiProvider).lista('/payment-accounts', query: {'all': todas ? 'true' : null}),
);

Uint8List? _bytesQr(String? dataUrl) {
  if (dataUrl == null) return null;
  final i = dataUrl.indexOf('base64,');
  if (i < 0) return null;
  try {
    return base64Decode(dataUrl.substring(i + 7));
  } catch (_) {
    return null;
  }
}

Widget _miniatura(String? dataUrl) {
  final q = _bytesQr(dataUrl);
  return q == null
      ? const Icon(Icons.account_balance, color: Tonos.gris)
      : Image.memory(q, filterQuality: FilterQuality.none);
}

String textoCuenta(Map<String, dynamic> a, {bool negrita = true}) {
  final b = negrita ? '*' : '';
  final tipo = _etiqueta(_tiposCuenta, a['account_type']);
  return [
    '$b${a['label']}$b',
    if (a['account_number'] != null)
      '${a['account_type'] != null ? tipo : 'Cuenta'} N.º ${a['account_number']}',
    if (a['holder_name'] != null) 'Titular: ${a['holder_name']}',
    if (a['holder_id'] != null) 'C.I./RUC: ${a['holder_id']}',
    if (a['email'] != null) 'Correo: ${a['email']}',
    if (a['note'] != null) '${a['note']}',
  ].join('\n');
}

String _etiqueta(List<Opcion> l, dynamic c) =>
    l.where((o) => o.$1 == c).map((o) => o.$2).firstOrNull ?? '${c ?? ''}';

Future<String?> _leerQr(Uint8List bytes) async {
  try {
    final codec = await ui.instantiateImageCodec(bytes);
    final cuadro = (await codec.getNextFrame()).image;
    final lado = cuadro.width > cuadro.height ? cuadro.width : cuadro.height;
    ui.Image img = cuadro;
    if (lado > 900) {
      final c2 = await ui.instantiateImageCodec(
        bytes,
        targetWidth: cuadro.width >= cuadro.height ? 900 : null,
        targetHeight: cuadro.height > cuadro.width ? 900 : null,
      );
      img = (await c2.getNextFrame()).image;
    }
    final png = await img.toByteData(format: ui.ImageByteFormat.png);
    if (png == null) return null;
    return 'data:image/png;base64,${base64Encode(png.buffer.asUint8List())}';
  } catch (_) {
    return null;
  }
}

Future<void> mostrarDatosPago(
  BuildContext context, {
  String? nombre,
  String? telefono,
  double? monto,
  String? concepto,
}) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    showDragHandle: true,
    constraints: const BoxConstraints(maxWidth: 680),
    builder: (_) => _HojaDatosPago(nombre: nombre, telefono: telefono, monto: monto, concepto: concepto),
  );
}

class _HojaDatosPago extends ConsumerWidget {
  const _HojaDatosPago({this.nombre, this.telefono, this.monto, this.concepto});
  final String? nombre;
  final String? telefono;
  final double? monto;
  final String? concepto;

  String _mensaje(List<Map<String, dynamic>> cuentas, String clinica) {
    final saludo = nombre != null ? 'Hola ${nombre!.split(' ').first}, ' : 'Hola, ';
    final valor = (monto ?? 0) > 0 ? 'el valor a pagar${concepto != null ? ' ($concepto)' : ''} es *${dinero(monto!)}*. ' : '';
    final cuerpo = cuentas
        .map((a) => textoCuenta(a) + (a['qr_data'] != null && a['account_number'] == null
            ? '\n(Pago con código QR: le enviamos la imagen a continuación)'
            : ''))
        .join('\n\n');
    final cierre = cuentas.any((a) => '${a['note'] ?? ''}'.toLowerCase().contains('comprobante'))
        ? 'Gracias.'
        : 'Por favor envíenos el comprobante por este medio. Gracias.';
    return '$saludo$valor${valor.isEmpty ? 'estos' : 'Estos'} son nuestros datos de pago:\n\n$cuerpo\n\n$cierre\n$clinica';
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final puedeConfigurar = ref.watch(authProvider).usuario?.puede('settings:manage') ?? false;
    final clinica = ref.watch(marcaProvider).nombre;
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.9,
      maxChildSize: 0.95,
      builder: (context, scroll) => ref
          .watch(cuentasPagoProvider(false))
          .when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => EstadoError(mensaje: e is ErrorApi ? e.mensaje : 'No se pudieron cargar los datos de pago.'),
            data: (cuentas) => ListView(
              controller: scroll,
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
              children: [
                const Text('Datos de pago', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
                if ((monto ?? 0) > 0) ...[
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.primary.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Text(
                      '${nombre != null ? '$nombre · ' : ''}${concepto ?? 'Valor a pagar'}: ${dinero(monto!)}',
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ),
                ],
                const SizedBox(height: 12),
                if (cuentas.isEmpty)
                  EstadoVacio(
                    icono: Icons.qr_code_2,
                    titulo: 'Aún no hay datos de pago',
                    detalle: 'Agrega el QR de tu banco o los datos de tu cuenta en Más › Datos de pago.',
                    accion: puedeConfigurar
                        ? FilledButton(
                            onPressed: () {
                              Navigator.pop(context);
                              Navigator.of(context).push(MaterialPageRoute(builder: (_) => const DatosPagoPage()));
                            },
                            child: const Text('Configurar ahora'),
                          )
                        : null,
                  )
                else ...[
                  for (final a in cuentas) _TarjetaCuenta(a),
                  const SizedBox(height: 8),
                  FilledButton.icon(
                    onPressed: () => abrirWhatsapp(context, telefono, _mensaje(cuentas, clinica)),
                    icon: const Icon(Icons.chat_outlined),
                    label: const Text('Enviar por WhatsApp'),
                  ),
                ],
              ],
            ),
          ),
    );
  }
}

class _TarjetaCuenta extends StatelessWidget {
  const _TarjetaCuenta(this.a);
  final Map<String, dynamic> a;

  Future<void> _ampliar(BuildContext context, Uint8List bytes) => showDialog<void>(
    context: context,
    barrierColor: Colors.black87,
    builder: (d) => GestureDetector(
      onTap: () => Navigator.pop(d),
      child: Center(
        child: Container(
          margin: const EdgeInsets.all(20),
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(18)),
          child: Image.memory(bytes, filterQuality: FilterQuality.none),
        ),
      ),
    ),
  );

  Future<void> _compartir(BuildContext context, Uint8List bytes) async {
    final dir = await getTemporaryDirectory();
    final f = File('${dir.path}/qr-${'${a['label']}'.replaceAll(RegExp(r'[^\w]+'), '-')}.png');
    await f.writeAsBytes(bytes, flush: true);
    final r = await OpenFilex.open(f.path, type: 'image/png');
    if (r.type != ResultType.done && context.mounted) avisar(context, 'No hay una aplicación para abrir imágenes.');
  }

  @override
  Widget build(BuildContext context) {
    final qr = _bytesQr(a['qr_data'] as String?);
    final datos = a['account_number'] != null || a['holder_name'] != null || a['email'] != null;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: GlassCard(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('${a['label']}', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
              if (qr != null) ...[
                const SizedBox(height: 10),
                GestureDetector(
                  onTap: () => _ampliar(context, qr),
                  child: Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxHeight: 260),
                      child: Image.memory(qr, filterQuality: FilterQuality.none),
                    ),
                  ),
                ),
                TextButton.icon(
                  onPressed: () => _compartir(context, qr),
                  icon: const Icon(Icons.share_outlined, size: 18),
                  label: const Text('Abrir QR para compartir'),
                ),
              ],
              if (datos) ...[
                const SizedBox(height: 6),
                Text(textoCuenta(a, negrita: false).split('\n').skip(1).join('\n'), style: const TextStyle(height: 1.4)),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: () async {
                    await Clipboard.setData(ClipboardData(text: textoCuenta(a, negrita: false)));
                    if (context.mounted) avisar(context, 'Datos copiados.');
                  },
                  icon: const Icon(Icons.copy, size: 18),
                  label: const Text('Copiar datos'),
                ),
              ] else if (a['note'] != null)
                Text('${a['note']}', style: const TextStyle(fontStyle: FontStyle.italic)),
            ],
          ),
        ),
      ),
    );
  }
}

class DatosPagoPage extends ConsumerWidget {
  const DatosPagoPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final api = ref.read(apiProvider);
    void refrescar() {
      ref.invalidate(cuentasPagoProvider(true));
      ref.invalidate(cuentasPagoProvider(false));
    }

    return PaginaModulo(
      titulo: 'Datos de pago',
      acciones: [
        IconButton(
          tooltip: 'Ver como el paciente',
          icon: const Icon(Icons.visibility_outlined),
          onPressed: () => mostrarDatosPago(context, nombre: 'Paciente de ejemplo', monto: 30, concepto: 'cuota'),
        ),
      ],
      accion: FloatingActionButton.extended(
        heroTag: 'fab-datos-pago',
        onPressed: () async {
          if (await editarCuentaPago(context, ref)) refrescar();
        },
        icon: const Icon(Icons.add),
        label: const Text('Agregar banco o QR'),
      ),
      cuerpo: RefreshIndicator(
        onRefresh: () async => refrescar(),
        child: Asincrono(
          valor: ref.watch(cuentasPagoProvider(true)),
          alReintentar: refrescar,
          esqueleto: const EsqueletoLista(filas: 3, conTarjetas: true),
          listo: (cuentas) => ListView(
            padding: const EdgeInsets.all(16),
            children: [
              const Text(
                'Tus bancos con su código QR y los datos para transferir. Se muestran al cobrar, en el portal del paciente y se envían por WhatsApp.',
                style: TextStyle(fontSize: 13),
              ),
              const SizedBox(height: 12),
              if (cuentas.isEmpty)
                const EstadoVacio(
                  icono: Icons.qr_code_2,
                  titulo: 'Aún no tienes datos de pago',
                  detalle: 'Sube la foto del QR de tu banco (Pichincha, Guayaquil, DeUna, PayPhone…) y/o tu número de cuenta.',
                )
              else
                for (var i = 0; i < cuentas.length; i++)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Opacity(
                      opacity: cuentas[i]['is_active'] == true ? 1 : 0.55,
                      child: GlassCard(
                        onTap: () async {
                          if (await editarCuentaPago(context, ref, cuentas[i])) refrescar();
                        },
                        child: Padding(
                          padding: const EdgeInsets.fromLTRB(12, 12, 4, 12),
                          child: Row(
                            children: [
                              Container(
                                width: 72,
                                height: 72,
                                padding: const EdgeInsets.all(4),
                                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
                                child: _miniatura(cuentas[i]['qr_data'] as String?),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text('${cuentas[i]['label']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                                    if (cuentas[i]['account_number'] != null)
                                      Text('N.º ${cuentas[i]['account_number']}', style: const TextStyle(fontSize: 12.5)),
                                    if (cuentas[i]['holder_name'] != null)
                                      Text('${cuentas[i]['holder_name']}', style: const TextStyle(fontSize: 12.5)),
                                    if (cuentas[i]['is_active'] != true) const Pastilla('Oculta', color: Tonos.gris),
                                  ],
                                ),
                              ),
                              PopupMenuButton<String>(
                                onSelected: (v) async {
                                  final id = '${cuentas[i]['id']}';
                                  switch (v) {
                                    case 'editar':
                                      if (await editarCuentaPago(context, ref, cuentas[i])) refrescar();
                                    case 'subir' || 'bajar':
                                      final ids = cuentas.map((c) => '${c['id']}').toList();
                                      final j = v == 'subir' ? i - 1 : i + 1;
                                      ids[i] = ids[j];
                                      ids[j] = id;
                                      if (await intentar(context, () => api.post('/payment-accounts/reorder', {'ids': ids}))) refrescar();
                                    case 'ocultar':
                                      if (await intentar(context,
                                          () => api.put('/payment-accounts/$id', {'is_active': cuentas[i]['is_active'] != true}))) {
                                        refrescar();
                                      }
                                    case 'eliminar':
                                      if (await confirmar(context,
                                              titulo: '¿Eliminar ${cuentas[i]['label']}?',
                                              mensaje: 'Si solo quieres dejar de mostrarla un tiempo, ocúltala.',
                                              textoConfirmar: 'Eliminar',
                                              peligro: true) &&
                                          context.mounted &&
                                          await intentar(context, () => api.delete('/payment-accounts/$id'))) {
                                        refrescar();
                                      }
                                  }
                                },
                                itemBuilder: (_) => [
                                  const PopupMenuItem(value: 'editar', child: Text('Editar')),
                                  if (i > 0) const PopupMenuItem(value: 'subir', child: Text('Subir')),
                                  if (i < cuentas.length - 1) const PopupMenuItem(value: 'bajar', child: Text('Bajar')),
                                  PopupMenuItem(
                                    value: 'ocultar',
                                    child: Text(cuentas[i]['is_active'] == true ? 'Ocultar' : 'Mostrar'),
                                  ),
                                  const PopupMenuItem(value: 'eliminar', child: Text('Eliminar')),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
              finDeLista,
            ],
          ),
        ),
      ),
    );
  }
}

Future<bool> editarCuentaPago(BuildContext context, WidgetRef ref, [Map<String, dynamic>? a]) async {
  String? qr = a?['qr_data'] as String?;
  final accion = await showModalBottomSheet<String>(
    context: context,
    showDragHandle: true,
    builder: (h) => SafeArea(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          ListTile(
            leading: const Icon(Icons.qr_code_2),
            title: Text(qr == null ? 'Subir la foto del QR' : 'Cambiar la foto del QR'),
            subtitle: const Text('La imagen que te da tu banco, DeUna, PayPhone u otro'),
            onTap: () => Navigator.pop(h, 'subir'),
          ),
          if (qr != null)
            ListTile(
              leading: const Icon(Icons.hide_image_outlined),
              title: const Text('Quitar el QR'),
              onTap: () => Navigator.pop(h, 'quitar'),
            ),
          ListTile(
            leading: const Icon(Icons.edit_note),
            title: Text(qr == null ? 'Continuar sin QR (solo datos de la cuenta)' : 'Conservar el QR y editar los datos'),
            onTap: () => Navigator.pop(h, 'seguir'),
          ),
        ],
      ),
    ),
  );
  if (accion == null || !context.mounted) return false;
  if (accion == 'quitar') qr = null;
  if (accion == 'subir') {
    final elegidos = await FilePicker.pickFiles(type: FileType.image);
    if (elegidos.isEmpty || !context.mounted) return false;
    final leido = await _leerQr(await elegidos.single.readAsBytes());
    if (!context.mounted) return false;
    if (leido == null) {
      avisar(context, 'No se pudo leer la imagen. Use una foto PNG o JPG.');
      return false;
    }
    qr = leido;
  }
  final r = await mostrarFormulario(
    context,
    titulo: a == null ? 'Agregar datos de pago' : 'Editar ${a['label']}',
    subtitulo: qr != null ? 'Código QR cargado.' : 'Sin código QR: escribe los datos de la cuenta.',
    icono: Icons.qr_code_2,
    campos: [
      Campo('label', 'Banco o medio de pago', requerido: true, inicial: a?['label'], ayuda: 'Ej.: Banco Pichincha, DeUna'),
      Campo('account_type', 'Tipo de cuenta', tipo: TipoCampo.seleccion, opciones: _tiposCuenta, inicial: a?['account_type'], mitad: true),
      Campo('account_number', 'Número de cuenta', inicial: a?['account_number'], mitad: true),
      Campo('holder_name', 'Titular', inicial: a?['holder_name'], mitad: true),
      Campo('holder_id', 'Cédula o RUC del titular', inicial: a?['holder_id'], mitad: true),
      Campo('email', 'Correo (opcional)', tipo: TipoCampo.correo, inicial: a?['email']),
      Campo('note', 'Nota para el paciente (opcional)', inicial: a?['note'], ayuda: 'Ej.: Envíe el comprobante por WhatsApp'),
      Campo('is_active', 'Mostrar a pacientes y al cobrar', tipo: TipoCampo.interruptor, inicial: a?['is_active'] ?? true),
    ],
    alGuardar: (v) async {
      final datos = {...v, 'qr_data': qr};
      if (qr == null && v['account_number'] == null && v['email'] == null) {
        throw ErrorApi('Sube el código QR o escribe los datos de la cuenta.');
      }
      final api = ref.read(apiProvider);
      if (a == null) {
        await api.post('/payment-accounts', datos);
      } else {
        await api.put('/payment-accounts/${a['id']}', datos);
      }
    },
  );
  return r != null;
}
