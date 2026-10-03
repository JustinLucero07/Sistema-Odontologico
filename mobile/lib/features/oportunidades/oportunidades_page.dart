import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/api/api.dart';
import '../../shared/contacto.dart';
import '../../shared/formato.dart';
import '../../shared/widgets/carga.dart';
import '../../shared/widgets/estado_vacio.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';
import '../pacientes/paciente_detalle_page.dart';

final oportunidadesProvider = FutureProvider.autoDispose<Map<String, dynamic>>(
  (ref) => ref.watch(apiProvider).mapa('/insights/opportunities'),
);

class _Grupo {
  const _Grupo(this.clave, this.titulo, this.icono, this.color, this.ayuda);
  final String clave;
  final String titulo;
  final IconData icono;
  final Color color;
  final String ayuda;
}

const _grupos = [
  _Grupo(
    'unconfirmed',
    'Citas de mañana sin confirmar',
    Icons.event_busy,
    Tonos.azul,
    'Confirmarlas hoy reduce las inasistencias.',
  ),
  _Grupo(
    'birthdays',
    'Cumpleaños esta semana',
    Icons.cake_outlined,
    Color(0xFFD81B60),
    'Un saludo a tiempo fideliza más que una promoción.',
  ),
  _Grupo(
    'pending_treatments',
    'Tratamientos aprobados sin cita',
    Icons.assignment_late_outlined,
    Tonos.ambar,
    'Aceptaron el tratamiento pero no tienen fecha.',
  ),
  _Grupo(
    'recall',
    'Pacientes por recuperar',
    Icons.person_search_outlined,
    Tonos.violeta,
    'Sin visita en 6 meses o más y sin cita.',
  ),
  _Grupo(
    'debtors',
    'Saldos pendientes',
    Icons.account_balance_wallet_outlined,
    Tonos.rojo,
    'Cargos sin pagar, de mayor a menor.',
  ),
];

String _primero(dynamic nombre) => '$nombre'.split(' ').first;

/// Detalle y mensaje listo para cada fila, igual que en la web.
(String, String?, String) _fila(
  String grupo,
  Map<String, dynamic> x,
  String clinica,
) {
  final n = _primero(x['patient_name']);
  switch (grupo) {
    case 'unconfirmed':
      final hora = DateFormat(
        'HH:mm',
      ).format(DateTime.parse('${x['starts_at']}').toLocal());
      return (
        'Mañana $hora · ${x['professional_name']}',
        null,
        'Hola $n, le escribimos de $clinica para confirmar su cita de mañana a las $hora con ${x['professional_name']}. ¿Nos confirma su asistencia? ¡Gracias!',
      );
    case 'birthdays':
      final d = x['days_until'] as int? ?? 0;
      return (
        d == 0
            ? '¡Hoy cumple ${x['turns']} años!'
            : 'Cumple ${x['turns']} en $d ${d == 1 ? 'día' : 'días'}',
        null,
        '¡Feliz cumpleaños, $n! 🎉 Todo el equipo de $clinica le desea un excelente día. Gracias por confiarnos su sonrisa.',
      );
    case 'pending_treatments':
      final t = (x['treatments'] as List? ?? []).join(', ');
      return (
        t,
        dinero(numero(x['amount'])),
        'Hola $n, le escribimos de $clinica. Tiene pendiente: $t. ¿Le gustaría que le agendemos una cita esta semana?',
      );
    case 'recall':
      return (
        'Última visita hace ${x['months_since']} meses',
        null,
        'Hola $n, en $clinica le recordamos que ya es momento de su control dental. ¿Le agendamos una cita?',
      );
    default:
      return (
        'Desde ${fechaCorta(x['oldest_charge_on'])}',
        dinero(numero(x['pending'])),
        'Hola $n, le escribimos de $clinica. Le recordamos que tiene un saldo pendiente de ${dinero(numero(x['pending']))}. Puede acercarse a cancelarlo o escribirnos para coordinar. ¡Gracias!',
      );
  }
}

/// Centro de oportunidades: a quién escribir hoy y por qué, con el mensaje
/// de WhatsApp ya escrito.
class OportunidadesPage extends ConsumerStatefulWidget {
  const OportunidadesPage({super.key});

  @override
  ConsumerState<OportunidadesPage> createState() => _OportunidadesPageState();
}

class _OportunidadesPageState extends ConsumerState<OportunidadesPage> {
  String? _activo;

  @override
  Widget build(BuildContext context) {
    return PaginaModulo(
      titulo: 'Oportunidades',
      cuerpo: RefreshIndicator(
        onRefresh: () async => ref.invalidate(oportunidadesProvider),
        child: Asincrono(
          valor: ref.watch(oportunidadesProvider),
          alReintentar: () => ref.invalidate(oportunidadesProvider),
          esqueleto: const EsqueletoLista(filas: 5, conTarjetas: true),
          listo: (d) {
            List<Map<String, dynamic>> l(String k) =>
                (d[k] as List? ?? []).cast<Map<String, dynamic>>();
            final activo =
                _activo ??
                _grupos
                    .where((g) => l(g.clave).isNotEmpty)
                    .firstOrNull
                    ?.clave ??
                _grupos.first.clave;
            final grupo = _grupos.firstWhere((g) => g.clave == activo);
            final clinica = '${d['clinic_name']}';
            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                SizedBox(
                  height: 112,
                  child: ListView(
                    scrollDirection: Axis.horizontal,
                    children: [
                      for (final g in _grupos)
                        Padding(
                          padding: const EdgeInsets.only(right: 10),
                          child: SizedBox(
                            width: 132,
                            child: _Tarjeta(
                              grupo: g,
                              cantidad: l(g.clave).length,
                              activa: g.clave == activo,
                              alTocar: () => setState(() => _activo = g.clave),
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
                Seccion(grupo.titulo),
                Padding(
                  padding: const EdgeInsets.fromLTRB(4, 0, 4, 10),
                  child: Text(
                    grupo.ayuda,
                    style: TextStyle(
                      fontSize: 12.5,
                      color: Theme.of(
                        context,
                      ).colorScheme.onSurface.withValues(alpha: 0.55),
                    ),
                  ),
                ),
                if (l(activo).isEmpty)
                  const EstadoVacio(
                    icono: Icons.task_alt,
                    titulo: 'Nada pendiente aquí',
                    detalle: '¡Buen trabajo!',
                  ),
                for (final x in l(activo))
                  Builder(
                    builder: (context) {
                      final (detalle, importe, mensaje) = _fila(
                        activo,
                        x,
                        clinica,
                      );
                      return FilaTarjeta(
                        icono: grupo.icono,
                        colorIcono: grupo.color,
                        titulo: '${x['patient_name']}',
                        subtitulo: importe == null
                            ? detalle
                            : '$detalle · $importe',
                        alTocar: () => Navigator.of(context).push(
                          MaterialPageRoute<void>(
                            builder: (_) => PacienteDetallePage(
                              pacienteId: '${x['patient_id']}',
                              nombre: '${x['patient_name']}',
                            ),
                          ),
                        ),
                        derecha: BotonesContacto(
                          telefono: x['phone'] as String?,
                          whatsapp: x['whatsapp'] as String?,
                          mensaje: mensaje,
                          permitido: x['contact_allowed'] != false,
                        ),
                      );
                    },
                  ),
                finDeLista,
              ],
            );
          },
        ),
      ),
    );
  }
}

class _Tarjeta extends StatelessWidget {
  const _Tarjeta({
    required this.grupo,
    required this.cantidad,
    required this.activa,
    required this.alTocar,
  });

  final _Grupo grupo;
  final int cantidad;
  final bool activa;
  final VoidCallback alTocar;

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        border: Border.all(
          color: activa ? grupo.color : Colors.transparent,
          width: 2,
        ),
      ),
      child: GlassCard(
        onTap: alTocar,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(grupo.icono, color: grupo.color, size: 22),
              const Spacer(),
              Text(
                '$cantidad',
                style: const TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.w800,
                ),
              ),
              Text(
                grupo.titulo,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 11, height: 1.2),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Resumen para el panel: cuántas oportunidades hay hoy.
int totalOportunidades(Map<String, dynamic> d) =>
    _grupos.fold(0, (s, g) => s + ((d[g.clave] as List?)?.length ?? 0));
