import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_controller.dart';
import '../../shared/widgets/glass.dart';

/// Acuerdo de confidencialidad, igual que en la web. Se muestra en lugar de
/// la app hasta que se acepta: nadie ve datos de pacientes sin haberlo hecho.
class ConfidencialidadPage extends ConsumerStatefulWidget {
  const ConfidencialidadPage({super.key});

  @override
  ConsumerState<ConfidencialidadPage> createState() =>
      _ConfidencialidadPageState();
}

class _ConfidencialidadPageState extends ConsumerState<ConfidencialidadPage> {
  bool _leido = false;
  bool _guardando = false;
  String? _error;
  String _clinica = 'la clínica';

  @override
  void initState() {
    super.initState();
    _cargarClinica();
  }

  Future<void> _cargarClinica() async {
    try {
      final r = await ref.read(apiClientProvider).dio.get('/legal/controller');
      final data = r.data as Map<String, dynamic>;
      if (!mounted) return;
      setState(
        () => _clinica =
            (data['legal_name'] ?? data['name'] ?? _clinica) as String,
      );
    } catch (_) {
      // Sin el nombre, el texto sigue siendo válido con "la clínica".
    }
  }

  Future<void> _aceptar() async {
    setState(() {
      _guardando = true;
      _error = null;
    });
    try {
      await ref.read(authProvider.notifier).aceptarConfidencialidad();
    } catch (_) {
      if (mounted) {
        setState(
          () =>
              _error = 'No se pudo registrar la aceptación. Intente de nuevo.',
        );
      }
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  /// Mismo texto que la web (frontend/src/app/shared/legal/legal-texts.ts).
  List<(String, List<String>)> get _secciones => [
    (
      'Compromiso',
      [
        'Al usar el sistema de $_clinica, usted accede a datos personales y de salud de pacientes, '
            'que la ley considera sensibles. Se compromete a guardar secreto sobre todo lo que conozca por este medio.',
      ],
    ),
    (
      'Qué implica',
      [
        'Acceder solo a la información que necesita para su trabajo, y únicamente con esa finalidad.',
        'No copiar, fotografiar, descargar, reenviar ni comentar datos de pacientes fuera de su función, '
            'ni por redes sociales o mensajería personal.',
        'No compartir su usuario ni su contraseña, y cerrar sesión o bloquear el equipo al dejarlo.',
        'Informar de inmediato a la dirección de la clínica cualquier pérdida, acceso indebido o incidente '
            'que afecte a los datos.',
      ],
    ),
    (
      'Registro y vigencia',
      [
        'Cada acceso a una historia clínica queda registrado con su usuario, fecha y hora.',
        'Este compromiso sigue vigente aun después de que termine su relación con la clínica. Su '
            'incumplimiento puede acarrear responsabilidades laborales, civiles y penales.',
      ],
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return AmbientBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: SafeArea(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 24, 20, 32),
            children: [
              Row(
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(16),
                      color: scheme.primary.withValues(alpha: 0.14),
                    ),
                    child: Icon(Icons.shield_outlined, color: scheme.primary),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Text(
                      'Acuerdo de confidencialidad',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                'Antes de continuar, lea y acepte cómo se protegen los datos de los pacientes.',
                style: TextStyle(
                  color: scheme.onSurface.withValues(alpha: 0.65),
                ),
              ),
              const SizedBox(height: 18),
              GlassPanel(
                padding: const EdgeInsets.all(18),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    for (final (titulo, parrafos) in _secciones) ...[
                      Text(
                        titulo,
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          color: scheme.primary,
                        ),
                      ),
                      const SizedBox(height: 6),
                      for (final p in parrafos)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: Text(p, style: const TextStyle(height: 1.45)),
                        ),
                      const SizedBox(height: 6),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 12),
              CheckboxListTile(
                value: _leido,
                onChanged: (v) => setState(() => _leido = v ?? false),
                controlAffinity: ListTileControlAffinity.leading,
                contentPadding: EdgeInsets.zero,
                title: const Text(
                  'He leído el acuerdo y me comprometo a cumplirlo.',
                  style: TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(_error!, style: TextStyle(color: scheme.error)),
                ),
              const SizedBox(height: 8),
              FilledButton(
                onPressed: _leido && !_guardando ? _aceptar : null,
                child: Text(_guardando ? 'Guardando…' : 'Aceptar y continuar'),
              ),
              const SizedBox(height: 8),
              TextButton(
                onPressed: () => ref.read(authProvider.notifier).cerrarSesion(),
                child: const Text('Salir'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
