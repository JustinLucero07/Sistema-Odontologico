import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/api/api.dart';
import '../../shared/abrir_pdf.dart';
import '../../shared/formato.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';

final comprobantesPacienteProvider = FutureProvider.autoDispose.family<List<Map<String, dynamic>>, String>(
  (ref, id) => ref.watch(apiProvider).lista('/patients/$id/portal-receipts'),
);

final comprobantesPendientesProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>(
  (ref) => ref.watch(apiProvider).lista('/portal-receipts/pending'),
);

String _fecha(dynamic iso) => DateFormat('dd/MM/yyyy').format(DateTime.parse('$iso'));

class ComprobantesPortal extends ConsumerWidget {
  const ComprobantesPortal({super.key, this.pacienteId, required this.puedeCobrar, this.alCambiar});

  final String? pacienteId;
  final bool puedeCobrar;
  final VoidCallback? alCambiar;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final id = pacienteId;
    final todos = (id == null ? ref.watch(comprobantesPendientesProvider) : ref.watch(comprobantesPacienteProvider(id))).valueOrNull;
    if (todos == null || todos.isEmpty) return const SizedBox.shrink();
    final items = [
      ...todos.where((c) => c['status'] == 'pendiente'),
      ...todos.where((c) => c['status'] != 'pendiente').take(3),
    ];
    final scheme = Theme.of(context).colorScheme;

    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: GlassCard(
        child: Container(
          decoration: const BoxDecoration(border: Border(left: BorderSide(color: Tonos.ambar, width: 3))),
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 6),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.receipt_long, color: Tonos.ambar),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      id == null ? 'Comprobantes por revisar' : 'Comprobantes del portal',
                      style: const TextStyle(fontWeight: FontWeight.w800),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 2),
              Text(
                'El paciente subió su transferencia. Revísela para registrar el pago.',
                style: TextStyle(fontSize: 12, color: scheme.onSurface.withValues(alpha: 0.6)),
              ),
              for (final c in items)
                Container(
                  padding: const EdgeInsets.symmetric(vertical: 9),
                  decoration: BoxDecoration(border: Border(top: BorderSide(color: scheme.outlineVariant.withValues(alpha: 0.5)))),
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(dinero(numero(c['amount'])), style: const TextStyle(fontWeight: FontWeight.w700)),
                            Text(
                              [
                                if (id == null && c['patient_name'] != null) '${c['patient_name']}',
                                '${c['destino']}',
                                'pagado el ${_fecha(c['paid_on'])}',
                              ].join(' · '),
                              style: TextStyle(fontSize: 12, color: scheme.onSurface.withValues(alpha: 0.65)),
                            ),
                            if (c['reject_reason'] != null)
                              Text('Rechazado: ${c['reject_reason']}', style: const TextStyle(fontSize: 12, color: Tonos.rojo)),
                          ],
                        ),
                      ),
                      if (c['status'] == 'pendiente' && puedeCobrar)
                        FilledButton.tonal(
                          key: Key('revisar-${c['id']}'),
                          style: FilledButton.styleFrom(minimumSize: const Size(0, 40)),
                          onPressed: () async {
                            if (await revisarComprobante(context, ref, c)) {
                              ref.invalidate(comprobantesPendientesProvider);
                              if (id != null) ref.invalidate(comprobantesPacienteProvider(id));
                              alCambiar?.call();
                            }
                          },
                          child: const Text('Revisar'),
                        )
                      else
                        _Estado(c),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Estado extends StatelessWidget {
  const _Estado(this.c);
  final Map<String, dynamic> c;

  @override
  Widget build(BuildContext context) {
    final color = switch (c['status']) {
      'aceptado' => Tonos.verde,
      'rechazado' => Tonos.rojo,
      _ => Tonos.ambar,
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
      decoration: BoxDecoration(color: color.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(99)),
      child: Text('${c['status_label']}', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: color)),
    );
  }
}

Future<bool> revisarComprobante(BuildContext context, WidgetRef ref, Map<String, dynamic> c) async {
  final r = await showModalBottomSheet<bool>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (_) => _HojaRevision(c: c),
  );
  return r == true;
}

class _HojaRevision extends ConsumerStatefulWidget {
  const _HojaRevision({required this.c});
  final Map<String, dynamic> c;

  @override
  ConsumerState<_HojaRevision> createState() => _HojaRevisionState();
}

class _HojaRevisionState extends ConsumerState<_HojaRevision> {
  late final _monto = TextEditingController(text: numero(widget.c['amount']).toStringAsFixed(2));
  String _metodo = 'transferencia';
  Uint8List? _archivo;
  bool _ocupado = false;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  @override
  void dispose() {
    _monto.dispose();
    super.dispose();
  }

  Future<void> _cargar() async {
    if (widget.c['mime_type'] == 'application/pdf') return;
    try {
      final b = await ref.read(apiProvider).bytes('/portal-receipts/${widget.c['id']}/file');
      if (mounted) setState(() => _archivo = Uint8List.fromList(b));
    } catch (_) {}
  }

  Future<void> _aceptar() async {
    final monto = double.tryParse(_monto.text.replaceAll(',', '.'));
    if (monto == null || monto <= 0) {
      avisar(context, 'Escriba un monto válido.');
      return;
    }
    setState(() => _ocupado = true);
    final ok = await intentar(
      context,
      () => ref.read(apiProvider).post('/portal-receipts/${widget.c['id']}/accept', {
        'amount': monto.toStringAsFixed(2),
        'method': _metodo,
      }),
      exito: 'Pago registrado',
    );
    if (!mounted) return;
    setState(() => _ocupado = false);
    if (ok) Navigator.pop(context, true);
  }

  Future<void> _rechazar() async {
    var hecho = false;
    await mostrarFormulario(
      context,
      titulo: 'Rechazar comprobante',
      subtitulo: 'El paciente verá el motivo en su portal.',
      icono: Icons.block,
      peligro: true,
      textoGuardar: 'Rechazar',
      campos: const [Campo('reason', 'Motivo', tipo: TipoCampo.multilinea, requerido: true)],
      alGuardar: (v) async {
        await ref.read(apiProvider).post('/portal-receipts/${widget.c['id']}/reject', {'reason': '${v['reason']}'.trim()});
        hecho = true;
      },
    );
    if (hecho && mounted) Navigator.pop(context, true);
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.c;
    final scheme = Theme.of(context).colorScheme;
    final tenue = TextStyle(fontSize: 12, color: scheme.onSurface.withValues(alpha: 0.6));
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('Revisar comprobante', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 12),
              ClipRRect(
                borderRadius: BorderRadius.circular(14),
                child: Container(
                  color: scheme.surfaceContainerHighest,
                  constraints: const BoxConstraints(minHeight: 120, maxHeight: 360),
                  alignment: Alignment.center,
                  child: c['mime_type'] == 'application/pdf'
                      ? Padding(
                          padding: const EdgeInsets.all(20),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.picture_as_pdf_outlined, size: 40, color: scheme.primary),
                              const SizedBox(height: 8),
                              const Text('El paciente envió el comprobante en PDF.', textAlign: TextAlign.center),
                              const SizedBox(height: 10),
                              FilledButton.tonalIcon(
                                key: const Key('abrir-pdf-comprobante'),
                                style: FilledButton.styleFrom(minimumSize: const Size(0, 40)),
                                onPressed: () => abrirArchivo(context, ref, '/portal-receipts/${c['id']}/file', 'comprobante-${c['id']}.pdf'),
                                icon: const Icon(Icons.open_in_new, size: 18),
                                label: const Text('Abrir PDF'),
                              ),
                            ],
                          ),
                        )
                      : _archivo == null
                      ? const Padding(padding: EdgeInsets.all(30), child: CircularProgressIndicator())
                      : InteractiveViewer(child: Image.memory(_archivo!, fit: BoxFit.contain)),
                ),
              ),
              const SizedBox(height: 12),
              if (c['patient_name'] != null) Text('${c['patient_name']}', style: const TextStyle(fontWeight: FontWeight.w700)),
              Text('${c['destino']} · pagado el ${_fecha(c['paid_on'])}', style: tenue),
              if (c['reference'] != null) Text('Referencia: ${c['reference']}', style: tenue),
              if (c['note'] != null) Text('Nota: ${c['note']}', style: tenue),
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      key: const Key('monto-comprobante'),
                      controller: _monto,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      decoration: const InputDecoration(labelText: 'Monto (\$)'),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      initialValue: _metodo,
                      isExpanded: true,
                      decoration: const InputDecoration(labelText: 'Medio'),
                      items: const [
                        DropdownMenuItem(value: 'transferencia', child: Text('Transferencia')),
                        DropdownMenuItem(value: 'deposito', child: Text('Depósito')),
                      ],
                      onChanged: (v) => setState(() => _metodo = v ?? 'transferencia'),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              FilledButton.icon(
                key: const Key('aceptar-comprobante'),
                onPressed: _ocupado ? null : _aceptar,
                icon: const Icon(Icons.check),
                label: const Text('Aceptar y registrar pago'),
              ),
              const SizedBox(height: 6),
              TextButton(
                onPressed: _ocupado ? null : _rechazar,
                style: TextButton.styleFrom(foregroundColor: Tonos.rojo),
                child: const Text('Rechazar'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
