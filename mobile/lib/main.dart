import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/date_symbol_data_local.dart';

import 'core/api/api_config.dart';
import 'core/auth/auth_controller.dart';
import 'core/marca/marca.dart';
import 'features/bienvenida/bienvenida_page.dart';
import 'core/theme/app_theme.dart';
import 'features/cuenta/cambiar_clave_page.dart';
import 'features/login/login_page.dart';
import 'shell.dart';
import 'features/legal/confidencialidad_page.dart';
import 'shared/widgets/carga.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Sin esto, `DateFormat('EEEE', 'es')` lanza: los datos del idioma se cargan
  // aparte y no vienen en el binario por defecto.
  await initializeDateFormatting('es');
  await ApiConfig.cargar();
  runApp(const ProviderScope(child: OdontoApp()));
}

class OdontoApp extends ConsumerStatefulWidget {
  const OdontoApp({super.key});

  @override
  ConsumerState<OdontoApp> createState() => _OdontoAppState();
}

class _OdontoAppState extends ConsumerState<OdontoApp> with WidgetsBindingObserver {
  final _avisos = GlobalKey<ScaffoldMessengerState>();
  DateTime _ultimaActividad = DateTime.now();
  Timer? _reloj;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    // Cierre por inactividad, con el tiempo que la consulta eligió en
    // Legal y cumplimiento (el mismo que usa la web).
    _reloj = Timer.periodic(const Duration(seconds: 30), (_) => _revisarInactividad());
    // Se intenta revivir la sesión antes de dibujar nada, para que quien ya
    // entró no vea parpadear el login.
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      // La marca guardada primero: el arranque y el login ya salen con el
      // logo y el color de la consulta.
      await ref.read(marcaProvider.notifier).cargarGuardada();
      ref.read(authProvider.notifier).restaurarSesion();
    });
  }

  @override
  void dispose() {
    _reloj?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState estado) {
    // Al volver de segundo plano se revisa antes de mostrar nada.
    if (estado == AppLifecycleState.resumed) _revisarInactividad();
  }

  void _revisarInactividad() {
    final minutos = ref.read(marcaProvider).sesionMinutos;
    if (minutos <= 0 || ref.read(authProvider).estado != EstadoSesion.autenticado) return;
    if (DateTime.now().difference(_ultimaActividad).inMinutes >= minutos) {
      _ultimaActividad = DateTime.now();
      ref.read(authProvider.notifier).cerrarSesion();
      _avisos.currentState?.showSnackBar(
        const SnackBar(content: Text('Se cerró la sesión por inactividad, para proteger los datos de los pacientes.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authProvider);
    final marca = ref.watch(marcaProvider);

    return MaterialApp(
      title: marca.nombre,
      debugShowCheckedModeBanner: false,
      scaffoldMessengerKey: _avisos,
      builder: (context, hijo) => Listener(
        behavior: HitTestBehavior.translucent,
        onPointerDown: (_) => _ultimaActividad = DateTime.now(),
        child: hijo,
      ),
      theme: lightTheme(),
      darkTheme: darkTheme(),
      themeMode: ThemeMode.system,
      // Calendarios, relojes y textos de Material en español.
      locale: const Locale('es'),
      supportedLocales: const [Locale('es'), Locale('en')],
      localizationsDelegates: GlobalMaterialLocalizations.delegates,
      home: switch (auth.estado) {
        EstadoSesion.cargando => const _Arranque(),
        // Primero la contraseña propia; después el acuerdo. Mismo orden que
        // en la web.
        EstadoSesion.autenticado when auth.usuario?.debeCambiarClave ?? false =>
          const CambiarClavePage(obligatorio: true),
        EstadoSesion.autenticado
            when auth.usuario?.confidencialidadPendiente ?? false =>
          const ConfidencialidadPage(),
        // Primer ingreso del administrador: el asistente de bienvenida.
        EstadoSesion.autenticado
            when !marca.configurada &&
                (auth.usuario?.puede('settings:manage') ?? false) =>
          const BienvenidaPage(),
        EstadoSesion.autenticado => const Shell(),
        EstadoSesion.anonimo => const LoginPage(),
      },
    );
  }
}

class _Arranque extends StatelessWidget {
  const _Arranque();

  @override
  Widget build(BuildContext context) {
    return const PantallaArranque();
  }
}
