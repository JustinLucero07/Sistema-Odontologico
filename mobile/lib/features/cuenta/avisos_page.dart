import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_controller.dart';
import '../../core/notificaciones/avisos_citas.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';

/// Ajustes de los avisos de citas de este teléfono.
class AvisosPage extends ConsumerStatefulWidget {
  const AvisosPage({super.key});

  @override
  ConsumerState<AvisosPage> createState() => _AvisosPageState();
}

class _AvisosPageState extends ConsumerState<AvisosPage> {
  final _avisos = AvisosCitas.instancia;
  late AjustesAvisos _a = _avisos.ajustes;

  @override
  void initState() {
    super.initState();
    _avisos.iniciar().then((_) {
      if (mounted) setState(() => _a = _avisos.ajustes);
    });
  }

  Future<void> _cambiar(AjustesAvisos nuevos) async {
    setState(() => _a = nuevos);
    await _avisos.guardarAjustes(nuevos);
    // Se rehacen con la configuración nueva.
    await _avisos.actualizar(ref.read(apiClientProvider).dio);
  }

  @override
  Widget build(BuildContext context) {
    return PaginaModulo(
      titulo: 'Avisos de citas',
      cuerpo: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Los avisos se programan en este teléfono con la agenda: llegan aunque la app esté cerrada o sin internet.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 12),
          GlassCard(
            child: Column(
              children: [
                SwitchListTile(
                  value: _a.activos,
                  onChanged: (v) async {
                    if (v) await _avisos.pedirPermiso();
                    await _cambiar(_a.copyWith(activos: v));
                  },
                  title: const Text('Avisos de citas'),
                  subtitle: const Text('Antes de cada cita de la agenda'),
                ),
                const Divider(height: 1),
                ListTile(
                  enabled: _a.activos,
                  title: const Text('Avisar antes'),
                  trailing: DropdownButton<int>(
                    value: _a.minutosAntes,
                    underline: const SizedBox.shrink(),
                    items: [
                      for (final m in const [10, 15, 30, 45, 60, 120])
                        DropdownMenuItem(value: m, child: Text(m < 60 ? '$m min' : '${m ~/ 60} h')),
                    ],
                    onChanged: _a.activos ? (m) => _cambiar(_a.copyWith(minutosAntes: m)) : null,
                  ),
                ),
                const Divider(height: 1),
                SwitchListTile(
                  value: _a.resumenDiario,
                  onChanged: _a.activos ? (v) => _cambiar(_a.copyWith(resumenDiario: v)) : null,
                  title: const Text('Resumen cada mañana'),
                  subtitle: Text('A las ${_a.horaResumen.toString().padLeft(2, '0')}:${_a.minutoResumen.toString().padLeft(2, '0')} · cuántas citas hay'),
                  secondary: IconButton(
                    tooltip: 'Cambiar hora',
                    icon: const Icon(Icons.schedule),
                    onPressed: !_a.activos
                        ? null
                        : () async {
                            final h = await showTimePicker(context: context, initialTime: TimeOfDay(hour: _a.horaResumen, minute: _a.minutoResumen));
                            if (h != null) await _cambiar(_a.copyWith(horaResumen: h.hour, minutoResumen: h.minute));
                          },
                  ),
                ),
                const Divider(height: 1),
                SwitchListTile(
                  value: _a.nuevasCitas,
                  onChanged: _a.activos ? (v) => _cambiar(_a.copyWith(nuevasCitas: v)) : null,
                  title: const Text('Citas nuevas'),
                  subtitle: const Text('Cuando otra persona agenda una cita'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: () async {
              final ok = await _avisos.pedirPermiso();
              await _avisos.probar();
              if (!ok && context.mounted) avisar(context, 'Active los avisos de esta app en los ajustes del teléfono.');
            },
            icon: const Icon(Icons.notifications_active_outlined),
            label: const Text('Probar aviso'),
          ),
          const Seccion('Recordatorios a los pacientes'),
          Text(
            'Los pacientes reciben recordatorios por WhatsApp y correo 24 h y 2 h antes de su cita, desde el servidor. '
            'El correo se configura en Más → Correo.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}
