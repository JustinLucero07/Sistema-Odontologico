import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_controller.dart';
import '../../shared/widgets/glass.dart';

/// Reglas de la contraseña. Son las mismas que aplica el servidor
/// (backend/app/core/password_policy.py); aquí solo se muestran mientras se
/// escribe, y quien decide de verdad es el servidor.
List<(String, bool)> reglasClave(
  String clave, {
  String nombre = '',
  String apellido = '',
  String email = '',
}) {
  final minusculas = clave.toLowerCase();
  final personales = [
    nombre,
    apellido,
    email.split('@').first,
  ].map((p) => p.trim().toLowerCase()).where((p) => p.length >= 3);
  return [
    ('Al menos 8 caracteres', clave.length >= 8),
    (
      'Letras y números',
      RegExp(r'[A-Za-zÁÉÍÓÚáéíóúÑñ]').hasMatch(clave) &&
          RegExp(r'\d').hasMatch(clave),
    ),
    (
      'Sin su nombre ni su correo',
      clave.isNotEmpty && !personales.any(minusculas.contains),
    ),
  ];
}

/// Fortaleza de 0 a 4 para la barra: largo y variedad de caracteres.
int fortalezaClave(String clave) {
  if (clave.isEmpty) return 0;
  var puntos = 0;
  if (clave.length >= 8) puntos++;
  if (clave.length >= 12) puntos++;
  if (RegExp(r'[a-z]').hasMatch(clave) && RegExp(r'[A-Z]').hasMatch(clave)) {
    puntos++;
  }
  if (RegExp(r'\d').hasMatch(clave) &&
      RegExp(r'[^A-Za-z0-9]').hasMatch(clave)) {
    puntos++;
  }
  return puntos.clamp(1, 4);
}

/// Cambio de contraseña, igual que en la web.
///
/// Con [obligatorio] se muestra en lugar de la app: quien entra con una
/// contraseña temporal puesta por el administrador no ve nada más hasta
/// elegir la suya.
class CambiarClavePage extends ConsumerStatefulWidget {
  const CambiarClavePage({super.key, this.obligatorio = false});

  final bool obligatorio;

  @override
  ConsumerState<CambiarClavePage> createState() => _CambiarClavePageState();
}

class _CambiarClavePageState extends ConsumerState<CambiarClavePage> {
  final _actual = TextEditingController();
  final _nueva = TextEditingController();
  final _repetida = TextEditingController();
  bool _ocultar = true;
  bool _guardando = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    for (final c in [_actual, _nueva, _repetida]) {
      c.addListener(() => setState(() {}));
    }
  }

  @override
  void dispose() {
    _actual.dispose();
    _nueva.dispose();
    _repetida.dispose();
    super.dispose();
  }

  Future<void> _guardar() async {
    setState(() {
      _guardando = true;
      _error = null;
    });
    final error = await ref
        .read(authProvider.notifier)
        .cambiarClave(_actual.text, _nueva.text);
    if (!mounted) return;
    setState(() {
      _guardando = false;
      _error = error;
    });
    if (error == null && !widget.obligatorio) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Contraseña cambiada. Se cerraron sus otras sesiones.'),
        ),
      );
      Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final usuario = ref.watch(authProvider).usuario;
    final reglas = reglasClave(
      _nueva.text,
      nombre: usuario?.nombre ?? '',
      apellido: usuario?.apellido ?? '',
      email: usuario?.email ?? '',
    );
    final fuerza = fortalezaClave(_nueva.text);
    final coincide = _nueva.text == _repetida.text;
    final distinta = _nueva.text != _actual.text;
    final listo =
        _actual.text.isNotEmpty &&
        reglas.every((r) => r.$2) &&
        coincide &&
        distinta &&
        !_guardando;

    final (nivel, colorNivel) = switch (fuerza) {
      0 => ('', scheme.outline),
      1 => ('Débil', scheme.error),
      2 => ('Aceptable', const Color(0xFFB9832F)),
      3 => ('Buena', scheme.primary),
      _ => ('Muy segura', const Color(0xFF2E7D32)),
    };

    final ojo = IconButton(
      tooltip: _ocultar ? 'Mostrar' : 'Ocultar',
      icon: Icon(_ocultar ? Icons.visibility_outlined : Icons.visibility_off),
      onPressed: () => setState(() => _ocultar = !_ocultar),
    );

    return AmbientBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: widget.obligatorio
            ? null
            : AppBar(
                backgroundColor: Colors.transparent,
                flexibleSpace: const GlassAppBarBackground(),
                title: const Text('Cambiar contraseña'),
              ),
        body: SafeArea(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 24, 20, 32),
            children: [
              if (widget.obligatorio) ...[
                Row(
                  children: [
                    Container(
                      width: 48,
                      height: 48,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(16),
                        color: scheme.primary.withValues(alpha: 0.14),
                      ),
                      child: Icon(Icons.lock_reset, color: scheme.primary),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Text(
                        'Elija su contraseña',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  'Entró con una contraseña temporal. Antes de continuar, cámbiela por una que solo usted conozca.',
                  style: TextStyle(
                    color: scheme.onSurface.withValues(alpha: 0.65),
                  ),
                ),
                const SizedBox(height: 18),
              ],
              GlassPanel(
                padding: const EdgeInsets.all(18),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    TextField(
                      controller: _actual,
                      obscureText: _ocultar,
                      autofillHints: const [AutofillHints.password],
                      textInputAction: TextInputAction.next,
                      decoration: InputDecoration(
                        labelText: widget.obligatorio
                            ? 'Contraseña temporal'
                            : 'Contraseña actual',
                        prefixIcon: const Icon(Icons.lock_outline),
                        suffixIcon: ojo,
                      ),
                    ),
                    const SizedBox(height: 14),
                    TextField(
                      controller: _nueva,
                      obscureText: _ocultar,
                      autofillHints: const [AutofillHints.newPassword],
                      textInputAction: TextInputAction.next,
                      decoration: InputDecoration(
                        labelText: 'Nueva contraseña',
                        prefixIcon: const Icon(Icons.key_outlined),
                        errorText: _nueva.text.isNotEmpty && !distinta
                            ? 'Debe ser distinta de la actual'
                            : null,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        for (var i = 1; i <= 4; i++)
                          Expanded(
                            child: AnimatedContainer(
                              duration: const Duration(milliseconds: 180),
                              height: 5,
                              margin: EdgeInsets.only(right: i < 4 ? 5 : 0),
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(3),
                                color: i <= fuerza
                                    ? colorNivel
                                    : scheme.onSurface.withValues(alpha: 0.12),
                              ),
                            ),
                          ),
                        SizedBox(
                          width: 86,
                          child: Text(
                            nivel,
                            textAlign: TextAlign.end,
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                              color: colorNivel,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    for (final (texto, cumple) in reglas)
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 3),
                        child: Row(
                          children: [
                            Icon(
                              cumple
                                  ? Icons.check_circle
                                  : Icons.radio_button_unchecked,
                              size: 17,
                              color: cumple
                                  ? scheme.primary
                                  : scheme.onSurface.withValues(alpha: 0.4),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              texto,
                              style: TextStyle(
                                fontSize: 13,
                                color: scheme.onSurface.withValues(
                                  alpha: cumple ? 0.9 : 0.6,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    const SizedBox(height: 14),
                    TextField(
                      controller: _repetida,
                      obscureText: _ocultar,
                      textInputAction: TextInputAction.done,
                      onSubmitted: (_) => listo ? _guardar() : null,
                      decoration: InputDecoration(
                        labelText: 'Repita la nueva contraseña',
                        prefixIcon: const Icon(Icons.key_outlined),
                        errorText: _repetida.text.isNotEmpty && !coincide
                            ? 'No coincide'
                            : null,
                      ),
                    ),
                  ],
                ),
              ),
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Text(_error!, style: TextStyle(color: scheme.error)),
                ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: listo ? _guardar : null,
                child: Text(_guardando ? 'Guardando…' : 'Cambiar contraseña'),
              ),
              const SizedBox(height: 8),
              if (widget.obligatorio)
                TextButton(
                  onPressed: () =>
                      ref.read(authProvider.notifier).cerrarSesion(),
                  child: const Text('Salir'),
                )
              else
                Text(
                  'Al cambiarla se cierran sus sesiones en otros dispositivos.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 12.5,
                    color: scheme.onSurface.withValues(alpha: 0.55),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
