import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_controller.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/widgets/tooth_mark.dart';

class LoginPage extends ConsumerStatefulWidget {
  const LoginPage({super.key});

  @override
  ConsumerState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends ConsumerState<LoginPage> {
  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _ocultar = true;
  bool _enviando = false;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _enviar() async {
    if (!_formKey.currentState!.validate() || _enviando) return;
    setState(() => _enviando = true);
    await ref
        .read(authProvider.notifier)
        .iniciarSesion(_email.text, _password.text);
    if (mounted) setState(() => _enviando = false);
  }

  @override
  Widget build(BuildContext context) {
    final error = ref.watch(authProvider).error;

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFF0F4C48), Color(0xFF0A3330), Color(0xFF07231F)],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 420),
                child: Form(
                  key: _formKey,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Center(
                        child: Container(
                          width: 64,
                          height: 64,
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(20),
                            color: AppColors.mint.withValues(alpha: 0.18),
                            border: Border.all(
                              color: Colors.white.withValues(alpha: 0.2),
                            ),
                          ),
                          child: const Center(
                            child: ToothMark(
                              size: 32,
                              color: Color(0xFF8BF0DE),
                              filled: true,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 22),
                      const Text(
                        'Sistema Odontológico',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.w700,
                          letterSpacing: -0.5,
                          color: Colors.white,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Ingresa con la cuenta de tu clínica.',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 14,
                          color: Colors.white.withValues(alpha: 0.7),
                        ),
                      ),
                      const SizedBox(height: 30),
                      _campo(
                        controller: _email,
                        label: 'Correo electrónico',
                        icon: Icons.alternate_email,
                        keyboardType: TextInputType.emailAddress,
                        validator: (v) {
                          if (v == null || v.trim().isEmpty) {
                            return 'El correo es obligatorio';
                          }
                          if (!v.contains('@')) {
                            return 'Ingresa un correo válido';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 14),
                      _campo(
                        controller: _password,
                        label: 'Contraseña',
                        icon: Icons.lock_outline,
                        obscure: _ocultar,
                        validator: (v) => (v == null || v.isEmpty)
                            ? 'La contraseña es obligatoria'
                            : null,
                        suffix: IconButton(
                          icon: Icon(
                            _ocultar ? Icons.visibility_off : Icons.visibility,
                            color: Colors.white.withValues(alpha: 0.6),
                          ),
                          onPressed: () => setState(() => _ocultar = !_ocultar),
                          tooltip: _ocultar
                              ? 'Mostrar contraseña'
                              : 'Ocultar contraseña',
                        ),
                      ),
                      if (error != null) ...[
                        const SizedBox(height: 16),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 14,
                            vertical: 12,
                          ),
                          decoration: BoxDecoration(
                            color: const Color(
                              0xFFFF8A80,
                            ).withValues(alpha: 0.16),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: const Color(
                                0xFFFF8A80,
                              ).withValues(alpha: 0.3),
                            ),
                          ),
                          child: Row(
                            children: [
                              const Icon(
                                Icons.error_outline,
                                size: 19,
                                color: Color(0xFFFFC7C2),
                              ),
                              const SizedBox(width: 9),
                              Expanded(
                                child: Text(
                                  error,
                                  style: const TextStyle(
                                    color: Color(0xFFFFC7C2),
                                    fontSize: 13,
                                    height: 1.35,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                      const SizedBox(height: 24),
                      FilledButton(
                        onPressed: _enviando ? null : _enviar,
                        style: FilledButton.styleFrom(
                          backgroundColor: AppColors.mint,
                          foregroundColor: const Color(0xFF04231F),
                        ),
                        child: _enviando
                            ? const SizedBox(
                                width: 22,
                                height: 22,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2.4,
                                  color: Color(0xFF04231F),
                                ),
                              )
                            : const Text('Ingresar'),
                      ),
                      const SizedBox(height: 22),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.shield_outlined,
                            size: 15,
                            color: Colors.white.withValues(alpha: 0.45),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            'Acceso auditado.',
                            style: TextStyle(
                              fontSize: 12,
                              color: Colors.white.withValues(alpha: 0.45),
                            ),
                          ),
                        ],
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

  Widget _campo({
    required TextEditingController controller,
    required String label,
    required IconData icon,
    TextInputType? keyboardType,
    bool obscure = false,
    Widget? suffix,
    String? Function(String?)? validator,
  }) {
    // Los campos de Material están pensados para una página clara; sobre el
    // degradado oscuro hay que darles tinta propia o desaparecen.
    const blanco = Colors.white;
    final tenue = blanco.withValues(alpha: 0.6);
    return TextFormField(
      controller: controller,
      obscureText: obscure,
      keyboardType: keyboardType,
      style: const TextStyle(color: blanco),
      cursorColor: AppColors.mint,
      validator: validator,
      decoration: InputDecoration(
        labelText: label,
        labelStyle: TextStyle(color: tenue),
        prefixIcon: Icon(icon, color: tenue, size: 20),
        suffixIcon: suffix,
        filled: true,
        fillColor: blanco.withValues(alpha: 0.08),
        errorStyle: const TextStyle(color: Color(0xFFFFC7C2)),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: blanco.withValues(alpha: 0.24)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: blanco.withValues(alpha: 0.24)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.mint, width: 2),
        ),
      ),
    );
  }
}
