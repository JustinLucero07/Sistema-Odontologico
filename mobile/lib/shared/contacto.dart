import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import 'widgets/formulario.dart';

/// Número en formato internacional para WhatsApp. Los números locales de
/// Ecuador (09…) pasan a 5939…, que es lo que exige wa.me.
String? numeroWhatsapp(String? numero) {
  if (numero == null) return null;
  var d = numero.replaceAll(RegExp(r'[^\d]'), '');
  if (d.length == 10 && d.startsWith('0')) d = '593${d.substring(1)}';
  return d.length < 8 ? null : d;
}

/// Abre WhatsApp con el mensaje escrito. No envía nada: la persona decide.
Future<void> abrirWhatsapp(
  BuildContext context,
  String? numero, [
  String mensaje = '',
]) async {
  final n = numeroWhatsapp(numero);
  if (n == null) {
    avisar(context, 'El paciente no tiene un número válido.');
    return;
  }
  final uri = Uri.parse(
    'https://wa.me/$n${mensaje.isEmpty ? '' : '?text=${Uri.encodeComponent(mensaje)}'}',
  );
  if (!await launchUrl(uri, mode: LaunchMode.externalApplication) &&
      context.mounted) {
    avisar(context, 'No se pudo abrir WhatsApp.');
  }
}

Future<void> llamar(BuildContext context, String? numero) async {
  if (numero == null || numero.trim().isEmpty) {
    avisar(context, 'Sin teléfono registrado.');
    return;
  }
  if (!await launchUrl(Uri(scheme: 'tel', path: numero.trim())) &&
      context.mounted) {
    avisar(context, 'No se pudo abrir el marcador.');
  }
}

/// Botones redondos de llamar y WhatsApp.
class BotonesContacto extends StatelessWidget {
  const BotonesContacto({
    super.key,
    required this.telefono,
    this.whatsapp,
    this.mensaje = '',
    this.permitido = true,
  });

  final String? telefono;
  final String? whatsapp;
  final String mensaje;

  /// Falso si el paciente retiró su autorización de comunicaciones.
  final bool permitido;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (telefono != null && telefono!.isNotEmpty)
          IconButton(
            tooltip: 'Llamar',
            onPressed: () => llamar(context, telefono),
            icon: const Icon(Icons.call_outlined),
          ),
        if (permitido && numeroWhatsapp(whatsapp ?? telefono) != null)
          IconButton.filled(
            tooltip: 'WhatsApp',
            style: IconButton.styleFrom(
              backgroundColor: const Color(0xFF1FA855),
              foregroundColor: Colors.white,
            ),
            onPressed: () =>
                abrirWhatsapp(context, whatsapp ?? telefono, mensaje),
            icon: const Icon(Icons.chat),
          )
        else if (!permitido)
          const Tooltip(
            message: 'Retiró su autorización de comunicaciones',
            child: Icon(Icons.block, size: 20),
          ),
      ],
    );
  }
}
