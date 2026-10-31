import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api.dart';
import '../../core/api/repositorios.dart';
import '../../core/auth/auth_controller.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';

/// Correo saliente de la consulta: el buzón desde el que salen facturas,
/// recordatorios de citas y consentimientos para firmar. Igual que en la web.

final _correoProvider = FutureProvider.autoDispose<Map<String, dynamic>>(
  (ref) => ref.watch(apiProvider).mapa('/mail/settings'),
);
final _proveedoresProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>(
  (ref) => ref.watch(apiProvider).lista('/mail/providers'),
);

class CorreoPage extends ConsumerWidget {
  const CorreoPage({super.key});

  Future<void> _editar(BuildContext context, WidgetRef ref, Map<String, dynamic> c) async {
    final proveedores = await cargarOAvisar(context, ref.read(_proveedoresProvider.future));
    if (proveedores == null || !context.mounted) return;
    // Primero el proveedor: rellena servidor, puerto y seguridad.
    final elegido = await showModalBottomSheet<Map<String, dynamic>>(
      context: context,
      builder: (hoja) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            for (final p in proveedores)
              ListTile(
                leading: const Icon(Icons.mail_outline),
                title: Text('${p['label']}'),
                subtitle: Text('${p['help']}', maxLines: 2, overflow: TextOverflow.ellipsis),
                onTap: () => Navigator.pop(hoja, p),
              ),
          ],
        ),
      ),
    );
    if (elegido == null || !context.mounted) return;
    final mismo = elegido['host'] == c['host'] || elegido['code'] == 'otro';
    await mostrarFormulario(
      context,
      titulo: '${elegido['label']}',
      subtitulo: '${elegido['help']}',
      icono: Icons.dns_outlined,
      campos: [
        Campo('host', 'Servidor SMTP', requerido: true, inicial: mismo && c['host'] != null ? c['host'] : elegido['host']),
        Campo('port', 'Puerto', tipo: TipoCampo.entero, requerido: true, mitad: true, inicial: mismo ? c['port'] : elegido['port']),
        Campo(
          'security',
          'Seguridad',
          tipo: TipoCampo.seleccion,
          requerido: true,
          mitad: true,
          opciones: const [('starttls', 'STARTTLS'), ('ssl', 'SSL/TLS'), ('none', 'Ninguna')],
          inicial: mismo ? c['security'] : elegido['security'],
        ),
        Campo('username', 'Usuario (su correo)', tipo: TipoCampo.correo, inicial: c['username']),
        Campo(
          'password',
          c['has_password'] == true ? 'Contraseña (vacía = conservar la guardada)' : 'Contraseña de aplicación',
          requerido: c['has_password'] != true,
        ),
        Campo('from_email', 'Correo del remitente', tipo: TipoCampo.correo, inicial: c['from_email'], ayuda: 'Normalmente el mismo de la cuenta.'),
        Campo('from_name', 'Nombre que verá el paciente', inicial: c['from_name']),
      ],
      alGuardar: (v) async {
        await ref.read(apiProvider).put('/mail/settings', {
          ...v,
          'from_email': (v['from_email'] as String?)?.isNotEmpty == true ? v['from_email'] : v['username'],
          if (v['password'] == null || '${v['password']}'.isEmpty) 'password': null,
        });
        ref.invalidate(_correoProvider);
      },
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final correoUsuario = ref.watch(authProvider).usuario?.email ?? '';
    return PaginaModulo(
      titulo: 'Correo',
      cuerpo: Asincrono(
        valor: ref.watch(_correoProvider),
        alReintentar: () => ref.invalidate(_correoProvider),
        listo: (c) {
          final listo = c['configured'] == true;
          final fallo = c['last_test_ok'] == false;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              FilaTarjeta(
                icono: !listo ? Icons.mail_lock_outlined : (fallo ? Icons.error_outline : Icons.mark_email_read_outlined),
                colorIcono: !listo || fallo ? Tonos.rojo : Tonos.verde,
                titulo: !listo
                    ? 'Sin correo configurado'
                    : c['source'] == 'servidor'
                    ? 'Usando el correo general del servidor'
                    : (fallo ? 'La última prueba falló' : '${c['from_email']}'),
                subtitulo: !listo
                    ? 'Las facturas van por WhatsApp o se descargan; los recordatorios, solo por WhatsApp.'
                    : (fallo ? '${c['last_error']}' : '${c['host']}:${c['port']}'),
              ),
              const Seccion('Configuración'),
              FilledButton.icon(
                onPressed: () => _editar(context, ref, c),
                icon: const Icon(Icons.edit_outlined),
                label: Text(c['source'] == 'consulta' ? 'Cambiar servidor de correo' : 'Configurar correo'),
              ),
              const SizedBox(height: 10),
              GlassCard(
                child: SwitchListTile(
                  value: c['reminders_enabled'] == true,
                  title: const Text('Recordatorios de citas por correo'),
                  subtitle: const Text('24 h y 2 h antes, además de WhatsApp'),
                  onChanged: (v) async {
                    if (await intentar(context, () => ref.read(apiProvider).put('/mail/settings', {'reminders_enabled': v}))) {
                      ref.invalidate(_correoProvider);
                    }
                  },
                ),
              ),
              const Seccion('Probar'),
              OutlinedButton.icon(
                onPressed: !listo
                    ? null
                    : () => mostrarFormulario(
                        context,
                        titulo: 'Correo de prueba',
                        icono: Icons.send_outlined,
                        textoGuardar: 'Enviar',
                        campos: [Campo('to', 'Enviar a', tipo: TipoCampo.correo, requerido: true, inicial: correoUsuario)],
                        alGuardar: (v) async {
                          final r = await ref.read(apiProvider).post('/mail/test', {'to': v['to']});
                          ref.invalidate(_correoProvider);
                          if (r is Map && r['last_test_ok'] != true) throw ErrorApi('${r['last_error']}');
                        },
                      ),
                icon: const Icon(Icons.send_outlined),
                label: const Text('Enviar correo de prueba'),
              ),
              if (c['source'] == 'consulta') ...[
                const SizedBox(height: 8),
                TextButton(
                  onPressed: () async {
                    if (!await confirmar(context, titulo: '¿Quitar el correo de la consulta?', textoConfirmar: 'Quitar', peligro: true)) return;
                    if (!context.mounted) return;
                    if (await intentar(context, () => ref.read(apiProvider).delete('/mail/settings'))) ref.invalidate(_correoProvider);
                  },
                  child: const Text('Quitar configuración'),
                ),
              ],
            ],
          );
        },
      ),
    );
  }
}
