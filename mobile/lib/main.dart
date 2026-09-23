import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/date_symbol_data_local.dart';

import 'core/auth/auth_controller.dart';
import 'core/theme/app_theme.dart';
import 'features/login/login_page.dart';
import 'shell.dart';
import 'features/legal/confidencialidad_page.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Sin esto, `DateFormat('EEEE', 'es')` lanza: los datos del idioma se cargan
  // aparte y no vienen en el binario por defecto.
  await initializeDateFormatting('es');
  runApp(const ProviderScope(child: OdontoApp()));
}

class OdontoApp extends ConsumerStatefulWidget {
  const OdontoApp({super.key});

  @override
  ConsumerState<OdontoApp> createState() => _OdontoAppState();
}

class _OdontoAppState extends ConsumerState<OdontoApp> {
  @override
  void initState() {
    super.initState();
    // Se intenta revivir la sesión antes de dibujar nada, para que quien ya
    // entró no vea parpadear el login.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(authProvider.notifier).restaurarSesion();
    });
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authProvider);

    return MaterialApp(
      title: 'Sistema Odontológico',
      debugShowCheckedModeBanner: false,
      theme: lightTheme(),
      darkTheme: darkTheme(),
      themeMode: ThemeMode.system,
      home: switch (auth.estado) {
        EstadoSesion.cargando => const _Arranque(),
        EstadoSesion.autenticado
            when auth.usuario?.confidencialidadPendiente ?? false =>
          const ConfidencialidadPage(),
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
    return const Scaffold(body: Center(child: CircularProgressIndicator()));
  }
}
