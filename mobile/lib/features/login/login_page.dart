import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_config.dart';
import '../../core/auth/auth_controller.dart';
import '../../core/marca/marca.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/widgets/carga.dart';
import '../../shared/widgets/tooth_mark.dart';

/// Ingreso. Es la primera impresión del producto, así que se cuida como una
/// portada: el diente de la marca se dibuja solo, aparece el nombre de la
/// consulta y sube una hoja de porcelana con el formulario.
///
/// Todo el movimiento de entrada dura poco más de dos segundos y no bloquea:
/// se puede escribir en cuanto la hoja asoma. Con «reducir movimiento» del
/// sistema se muestra directamente el estado final.
class LoginPage extends ConsumerStatefulWidget {
  const LoginPage({super.key});

  @override
  ConsumerState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends ConsumerState<LoginPage>
    with TickerProviderStateMixin {
  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _ocultar = true;
  bool _enviando = false;

  /// Coreografía de entrada (una sola vez).
  late final AnimationController _entrada = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 2300),
  );

  /// Luz de fondo y anillos: lentos y continuos, casi imperceptibles.
  late final AnimationController _ambiente = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 16),
  );
  late final AnimationController _pulso = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 3600),
  );

  /// Temblor de la hoja cuando el acceso falla.
  late final AnimationController _temblor = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 520),
  );

  bool _iniciado = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_iniciado) return;
    _iniciado = true;
    if (MediaQuery.of(context).disableAnimations) {
      _entrada.value = 1;
    } else {
      _entrada.forward();
      _ambiente.repeat();
      _pulso.repeat();
    }
  }

  @override
  void dispose() {
    _entrada.dispose();
    _ambiente.dispose();
    _pulso.dispose();
    _temblor.dispose();
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _cambiarServidor() async {
    final control = TextEditingController(
      text: ApiConfig.configurado ? ApiConfig.servidorVisible : '',
    );
    final nuevo = await showDialog<String>(
      context: context,
      builder: (dialogo) => AlertDialog(
        title: const Text('Servidor del consultorio'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'La dirección web donde su consultorio o clínica usa el sistema. '
              'Se configura una sola vez.',
            ),
            const SizedBox(height: 14),
            TextField(
              controller: control,
              autofocus: true,
              keyboardType: TextInputType.url,
              autocorrect: false,
              decoration: const InputDecoration(
                labelText: 'Dirección',
                hintText: 'clinica.ejemplo.com',
                prefixIcon: Icon(Icons.dns_outlined),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogo),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(minimumSize: const Size(100, 44)),
            onPressed: () => Navigator.pop(dialogo, control.text),
            child: const Text('Guardar'),
          ),
        ],
      ),
    );
    control.dispose();
    if (nuevo == null || nuevo.trim().isEmpty) return;
    await ApiConfig.guardar(nuevo);
    if (mounted) setState(() {});
  }

  Future<void> _enviar() async {
    if (!ApiConfig.configurado) {
      await _cambiarServidor();
      if (!ApiConfig.configurado) return;
    }
    if (!_formKey.currentState!.validate()) {
      _temblar();
      return;
    }
    if (_enviando || !mounted) return;
    FocusScope.of(context).unfocus();
    setState(() => _enviando = true);
    await ref
        .read(authProvider.notifier)
        .iniciarSesion(_email.text, _password.text);
    if (mounted) setState(() => _enviando = false);
  }

  void _temblar() {
    if (MediaQuery.of(context).disableAnimations) return;
    _temblor.forward(from: 0);
  }

  /// Tramo [a, b] de la entrada, con curva suave de salida.
  Animation<double> _tramo(double a, double b, [Curve curva = Curves.easeOutCubic]) =>
      CurvedAnimation(parent: _entrada, curve: Interval(a, b, curve: curva));

  @override
  Widget build(BuildContext context) {
    final error = ref.watch(authProvider).error;
    final marca = ref.watch(marcaProvider);
    ref.listen(authProvider.select((s) => s.error), (antes, ahora) {
      if (ahora != null && ahora != antes) _temblar();
    });

    final oscuroSistema = Theme.of(context).brightness == Brightness.dark;
    final fondo = tono(AppColors.primary, oscuroSistema ? -0.84 : -0.74);
    final teclado = MediaQuery.viewInsetsOf(context).bottom > 0;

    return Scaffold(
      backgroundColor: fondo,
      body: Stack(
        children: [
          Positioned.fill(
            child: _FondoVivo(animacion: _ambiente, color: AppColors.primary),
          ),
          SafeArea(
            bottom: false,
            child: Column(
              children: [
                Expanded(
                  child: _Portada(
                    entrada: _entrada,
                    pulso: _pulso,
                    tramo: _tramo,
                    nombre: marca.nombre,
                    eslogan: (marca.eslogan?.trim().isNotEmpty ?? false)
                        ? marca.eslogan!.trim()
                        : 'Gestión clínica odontológica',
                    compacta: teclado,
                  ),
                ),
                AnimatedBuilder(
                  animation: _temblor,
                  builder: (context, hijo) {
                    // Oscilación amortiguada: tres idas y vueltas que se apagan.
                    final t = _temblor.value;
                    final dx = math.sin(t * math.pi * 6) * 12 * (1 - t);
                    return Transform.translate(offset: Offset(dx, 0), child: hijo);
                  },
                  child: SlideTransition(
                    position: Tween(
                      begin: const Offset(0, 1),
                      end: Offset.zero,
                    ).animate(_tramo(0.42, 0.86, Curves.easeOutQuart)),
                    child: _hoja(context, error),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _hoja(BuildContext context, String? error) {
    final tema = Theme.of(context);
    final oscuro = tema.brightness == Brightness.dark;
    final tinta = oscuro ? AppColors.inkDark : AppColors.inkLight;
    final suave = tinta.withValues(alpha: 0.55);

    // Cada elemento de la hoja entra un instante después del anterior.
    Widget escalon(int i, Widget hijo) {
      final a = 0.56 + i * 0.05;
      final anim = _tramo(a, math.min(a + 0.3, 1));
      return FadeTransition(
        opacity: anim,
        child: SlideTransition(
          position: Tween(begin: const Offset(0, 0.35), end: Offset.zero).animate(anim),
          child: hijo,
        ),
      );
    }

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: oscuro ? AppColors.baseDark : AppColors.baseLight,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(34)),
        boxShadow: const [
          BoxShadow(color: Color(0x40000000), blurRadius: 40, offset: Offset(0, -8)),
        ],
      ),
      child: SafeArea(
        top: false,
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 460),
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(24, 14, 24, 16),
              child: AutofillGroup(
                child: Form(
                  key: _formKey,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Center(
                        child: Container(
                          width: 38,
                          height: 4,
                          decoration: BoxDecoration(
                            color: tinta.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(2),
                          ),
                        ),
                      ),
                      const SizedBox(height: 22),
                      escalon(
                        0,
                        Text('Bienvenido', style: estiloTitulo(26, color: tinta, peso: FontWeight.w800)),
                      ),
                      const SizedBox(height: 4),
                      escalon(
                        0,
                        Text(
                          'Ingrese con su cuenta del consultorio.',
                          style: TextStyle(fontSize: 14.5, color: suave),
                        ),
                      ),
                      const SizedBox(height: 22),
                      escalon(
                        1,
                        TextFormField(
                          controller: _email,
                          keyboardType: TextInputType.emailAddress,
                          autofillHints: const [AutofillHints.email, AutofillHints.username],
                          textInputAction: TextInputAction.next,
                          // Un correo no se autocorrige ni se capitaliza: el
                          // teclado lo «arreglaría» y el acceso fallaría.
                          autocorrect: false,
                          enableSuggestions: false,
                          decoration: const InputDecoration(
                            labelText: 'Correo electrónico',
                            prefixIcon: Icon(Icons.alternate_email_rounded, size: 20),
                          ),
                          validator: (v) {
                            if (v == null || v.trim().isEmpty) return 'El correo es obligatorio';
                            if (!v.contains('@')) return 'Ingrese un correo válido';
                            return null;
                          },
                        ),
                      ),
                      const SizedBox(height: 12),
                      escalon(
                        2,
                        TextFormField(
                          controller: _password,
                          obscureText: _ocultar,
                          autofillHints: const [AutofillHints.password],
                          textInputAction: TextInputAction.done,
                          onFieldSubmitted: (_) => _enviar(),
                          autocorrect: false,
                          enableSuggestions: false,
                          decoration: InputDecoration(
                            labelText: 'Contraseña',
                            prefixIcon: const Icon(Icons.lock_outline_rounded, size: 20),
                            suffixIcon: IconButton(
                              icon: AnimatedSwitcher(
                                duration: const Duration(milliseconds: 180),
                                child: Icon(
                                  _ocultar ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                                  key: ValueKey(_ocultar),
                                  size: 20,
                                ),
                              ),
                              onPressed: () => setState(() => _ocultar = !_ocultar),
                              tooltip: _ocultar ? 'Mostrar contraseña' : 'Ocultar contraseña',
                            ),
                          ),
                          validator: (v) =>
                              (v == null || v.isEmpty) ? 'La contraseña es obligatoria' : null,
                        ),
                      ),
                      AnimatedSize(
                        duration: const Duration(milliseconds: 260),
                        curve: Curves.easeOutCubic,
                        child: error == null
                            ? const SizedBox(width: double.infinity)
                            : Padding(
                                padding: const EdgeInsets.only(top: 14),
                                child: _AvisoError(texto: error),
                              ),
                      ),
                      const SizedBox(height: 20),
                      escalon(3, _BotonIngresar(enviando: _enviando, onPressed: _enviar)),
                      const SizedBox(height: 10),
                      escalon(
                        4,
                        Column(
                          children: [
                            if (!ApiConfig.esFijo)
                              TextButton.icon(
                                onPressed: _cambiarServidor,
                                style: TextButton.styleFrom(foregroundColor: suave),
                                icon: const Icon(Icons.dns_outlined, size: 17),
                                label: Text(
                                  ApiConfig.configurado
                                      ? 'Servidor: ${ApiConfig.servidorVisible}'
                                      : 'Configurar servidor del consultorio',
                                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
                                ),
                              ),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.verified_user_outlined, size: 14, color: tinta.withValues(alpha: 0.38)),
                                const SizedBox(width: 6),
                                Text(
                                  'Conexión cifrada · Acceso auditado',
                                  style: TextStyle(fontSize: 12, color: tinta.withValues(alpha: 0.42)),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Parte superior: logo animado, nombre y eslogan de la consulta.
class _Portada extends StatelessWidget {
  const _Portada({
    required this.entrada,
    required this.pulso,
    required this.tramo,
    required this.nombre,
    required this.eslogan,
    required this.compacta,
  });

  final AnimationController entrada;
  final AnimationController pulso;
  final Animation<double> Function(double, double, [Curve]) tramo;
  final String nombre;
  final String eslogan;
  final bool compacta;

  @override
  Widget build(BuildContext context) {
    final textoNombre = tramo(0.36, 0.66);
    final textoEslogan = tramo(0.46, 0.76);

    return LayoutBuilder(
      builder: (context, c) {
        // Con el teclado abierto queda poco alto: solo el logo, más pequeño.
        final sinTexto = compacta || c.maxHeight < 210;
        final logo = (c.maxHeight * (sinTexto ? 0.62 : 0.34)).clamp(40.0, 104.0);
        return Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              SizedBox(
                width: logo * 2.2,
                height: logo * 1.5,
                child: Stack(
                  alignment: Alignment.center,
                  clipBehavior: Clip.none,
                  children: [
                    Positioned.fill(
                      child: OverflowBox(
                        maxWidth: logo * 4,
                        maxHeight: logo * 4,
                        child: SizedBox(
                          width: logo * 4,
                          height: logo * 4,
                          child: _Anillos(pulso: pulso, aparicion: tramo(0.4, 0.8), radioBase: logo * 0.62),
                        ),
                      ),
                    ),
                    Marca.logoBytes != null
                        ? ScaleTransition(
                            scale: Tween(begin: 0.7, end: 1.0).animate(tramo(0, 0.45, Curves.easeOutBack)),
                            child: FadeTransition(
                              opacity: tramo(0, 0.3),
                              child: LogoApp(tamano: logo),
                            ),
                          )
                        : _LogoDibujado(entrada: entrada, tamano: logo),
                  ],
                ),
              ),
              if (!sinTexto) ...[
                const SizedBox(height: 18),
                FadeTransition(
                  opacity: textoNombre,
                  child: SlideTransition(
                    position: Tween(begin: const Offset(0, 0.4), end: Offset.zero).animate(textoNombre),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 28),
                      child: Text(
                        nombre,
                        textAlign: TextAlign.center,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: estiloTitulo(28, color: Colors.white, peso: FontWeight.w800),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                FadeTransition(
                  opacity: textoEslogan,
                  child: Text(
                    eslogan.toUpperCase(),
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 11.5,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 2.2,
                      color: tono(AppColors.primary, 0.55).withValues(alpha: 0.85),
                    ),
                  ),
                ),
              ],
            ],
          ),
        );
      },
    );
  }
}

/// El molar se dibuja a mano alzada: primero el contorno, luego se llena de
/// blanco y un destello cruza el esmalte.
class _LogoDibujado extends StatelessWidget {
  const _LogoDibujado({required this.entrada, required this.tamano});

  final AnimationController entrada;
  final double tamano;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: entrada,
      builder: (context, _) {
        double en(double a, double b, [Curve c = Curves.easeInOutCubic]) =>
            c.transform(((entrada.value - a) / (b - a)).clamp(0.0, 1.0));
        final escala = 0.86 + 0.14 * en(0.3, 0.6, Curves.easeOutBack);
        return Transform.scale(
          scale: escala,
          child: SizedBox(
            width: tamano,
            height: tamano,
            child: CustomPaint(
              painter: _DientePintor(
                trazo: en(0.02, 0.42),
                relleno: en(0.34, 0.56, Curves.easeOutCubic),
                destello: en(0.5, 0.74, Curves.easeInOutSine),
                acento: tono(AppColors.primary, 0.55),
              ),
            ),
          ),
        );
      },
    );
  }
}

class _DientePintor extends CustomPainter {
  _DientePintor({
    required this.trazo,
    required this.relleno,
    required this.destello,
    required this.acento,
  });

  final double trazo;
  final double relleno;
  final double destello;
  final Color acento;

  @override
  void paint(Canvas canvas, Size size) {
    final k = size.width / 32;
    final contorno = trazoDiente(k);

    // Halo suave detrás del diente cuando ya está lleno.
    if (relleno > 0) {
      canvas.drawCircle(
        Offset(16 * k, 16 * k),
        15 * k,
        Paint()
          ..color = acento.withValues(alpha: 0.22 * relleno)
          ..maskFilter = MaskFilter.blur(BlurStyle.normal, 9 * k),
      );
      canvas.drawPath(contorno, Paint()..color = Colors.white.withValues(alpha: relleno));
    }

    // Contorno dibujándose: se extrae la parte ya recorrida de la línea.
    final lapiz = Paint()
      ..color = Color.lerp(acento, Colors.white, relleno)!
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5 * k
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    for (final m in contorno.computeMetrics()) {
      canvas.drawPath(m.extractPath(0, m.length * trazo), lapiz);
      // La punta del lápiz brilla mientras dibuja.
      if (trazo > 0 && trazo < 1) {
        final punta = m.getTangentForOffset(m.length * trazo)?.position;
        if (punta != null) {
          canvas.drawCircle(
            punta,
            2.2 * k,
            Paint()
              ..color = Colors.white
              ..maskFilter = MaskFilter.blur(BlurStyle.normal, 1.6 * k),
          );
        }
      }
    }

    // Brillo del esmalte, que aparece con el relleno.
    if (relleno > 0.5) {
      canvas.drawPath(
        brilloDiente(k),
        Paint()
          ..color = tono(AppColors.primary, -0.6).withValues(alpha: 0.5 * (relleno - 0.5) * 2)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.6 * k
          ..strokeCap = StrokeCap.round,
      );
    }

    // Destello diagonal que cruza el diente una vez, recortado a su forma.
    if (destello > 0 && destello < 1) {
      canvas.save();
      canvas.clipPath(contorno);
      final x = (-10 + 52 * destello) * k;
      final rect = Rect.fromLTWH(x - 6 * k, 0, 12 * k, 32 * k);
      canvas.translate(x, 16 * k);
      canvas.rotate(0.38);
      canvas.translate(-x, -16 * k);
      canvas.drawRect(
        rect,
        Paint()
          ..shader = LinearGradient(
            colors: [
              acento.withValues(alpha: 0),
              acento.withValues(alpha: 0.55),
              acento.withValues(alpha: 0),
            ],
          ).createShader(rect),
      );
      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(_DientePintor old) =>
      old.trazo != trazo || old.relleno != relleno || old.destello != destello;
}

/// Ondas que salen del logo, como un latido tranquilo.
class _Anillos extends StatelessWidget {
  const _Anillos({required this.pulso, required this.aparicion, required this.radioBase});

  final AnimationController pulso;
  final Animation<double> aparicion;
  final double radioBase;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: Listenable.merge([pulso, aparicion]),
      builder: (context, _) => CustomPaint(
        painter: _AnillosPintor(
          t: pulso.value,
          visible: aparicion.value,
          radioBase: radioBase,
          color: tono(AppColors.primary, 0.5),
        ),
      ),
    );
  }
}

class _AnillosPintor extends CustomPainter {
  _AnillosPintor({required this.t, required this.visible, required this.radioBase, required this.color});

  final double t;
  final double visible;
  final double radioBase;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    if (visible == 0) return;
    final centro = size.center(Offset.zero);
    // Un anillo fijo, finísimo, que enmarca el logo.
    canvas.drawCircle(
      centro,
      radioBase * 1.18,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1
        ..color = color.withValues(alpha: 0.16 * visible),
    );
    // Tres ondas desfasadas que crecen y se desvanecen.
    for (var i = 0; i < 3; i++) {
      final f = (t + i / 3) % 1;
      final r = radioBase * (1.18 + f * 1.6);
      canvas.drawCircle(
        centro,
        r,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1
          ..color = color.withValues(alpha: 0.2 * (1 - f) * visible),
      );
    }
  }

  @override
  bool shouldRepaint(_AnillosPintor old) => old.t != t || old.visible != visible;
}

/// Dos luces muy difusas que derivan despacio por el fondo oscuro.
class _FondoVivo extends StatelessWidget {
  const _FondoVivo({required this.animacion, required this.color});

  final AnimationController animacion;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return RepaintBoundary(
      child: AnimatedBuilder(
        animation: animacion,
        builder: (context, _) {
          final a = animacion.value * 2 * math.pi;
          return CustomPaint(
            painter: _LucesPintor(
              p1: Alignment(-0.6 + 0.35 * math.cos(a), -0.75 + 0.15 * math.sin(a)),
              p2: Alignment(0.7 + 0.25 * math.sin(a), -0.15 + 0.2 * math.cos(a)),
              c1: tono(color, 0.15),
              c2: AppColors.accent,
            ),
          );
        },
      ),
    );
  }
}

class _LucesPintor extends CustomPainter {
  _LucesPintor({required this.p1, required this.p2, required this.c1, required this.c2});

  final Alignment p1;
  final Alignment p2;
  final Color c1;
  final Color c2;

  @override
  void paint(Canvas canvas, Size size) {
    void luz(Alignment a, Color c, double radio, double alfa) {
      final centro = a.alongSize(size);
      final r = size.shortestSide * radio;
      canvas.drawCircle(
        centro,
        r,
        Paint()
          ..shader = RadialGradient(
            colors: [c.withValues(alpha: alfa), c.withValues(alpha: 0)],
          ).createShader(Rect.fromCircle(center: centro, radius: r)),
      );
    }

    luz(p1, c1, 0.95, 0.42);
    luz(p2, c2, 0.7, 0.14);
  }

  @override
  bool shouldRepaint(_LucesPintor old) => old.p1 != p1 || old.p2 != p2;
}

class _AvisoError extends StatelessWidget {
  const _AvisoError({required this.texto});

  final String texto;

  @override
  Widget build(BuildContext context) {
    final rojo = Theme.of(context).colorScheme.error;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: rojo.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: rojo.withValues(alpha: 0.22)),
      ),
      child: Row(
        children: [
          Icon(Icons.error_outline_rounded, size: 19, color: rojo),
          const SizedBox(width: 10),
          Expanded(
            child: Text(texto, style: TextStyle(color: rojo, fontSize: 13, height: 1.35)),
          ),
        ],
      ),
    );
  }
}

/// Botón principal: tinta oscura, con la flecha que avanza al presionarlo.
class _BotonIngresar extends StatefulWidget {
  const _BotonIngresar({required this.enviando, required this.onPressed});

  final bool enviando;
  final VoidCallback onPressed;

  @override
  State<_BotonIngresar> createState() => _BotonIngresarState();
}

class _BotonIngresarState extends State<_BotonIngresar> {
  bool _abajo = false;

  @override
  Widget build(BuildContext context) {
    final oscuro = Theme.of(context).brightness == Brightness.dark;
    final fondo = oscuro ? AppColors.primaryOnDark : AppColors.inkLight;
    final texto = oscuro ? const Color(0xFF04201D) : Colors.white;
    return Listener(
      onPointerDown: (_) => setState(() => _abajo = true),
      onPointerUp: (_) => setState(() => _abajo = false),
      onPointerCancel: (_) => setState(() => _abajo = false),
      child: AnimatedScale(
        scale: _abajo ? 0.975 : 1,
        duration: Duration(milliseconds: _abajo ? 90 : 220),
        curve: Curves.easeOutCubic,
        child: FilledButton(
          onPressed: widget.enviando ? null : widget.onPressed,
          style: FilledButton.styleFrom(
            minimumSize: const Size.fromHeight(56),
            backgroundColor: fondo,
            foregroundColor: texto,
            disabledBackgroundColor: fondo.withValues(alpha: 0.85),
            disabledForegroundColor: texto,
          ),
          child: AnimatedSwitcher(
            duration: const Duration(milliseconds: 220),
            child: widget.enviando
                ? SizedBox(
                    key: const ValueKey('cargando'),
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(strokeWidth: 2.2, color: texto),
                  )
                : Row(
                    key: const ValueKey('texto'),
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Text('Ingresar', style: TextStyle(fontSize: 15.5, fontWeight: FontWeight.w600)),
                      AnimatedPadding(
                        duration: const Duration(milliseconds: 220),
                        curve: Curves.easeOutCubic,
                        padding: EdgeInsets.only(left: _abajo ? 14 : 8),
                        child: const Icon(Icons.arrow_forward_rounded, size: 19),
                      ),
                    ],
                  ),
          ),
        ),
      ),
    );
  }
}
