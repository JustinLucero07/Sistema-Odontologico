import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

import '../core/api/api.dart';
import 'widgets/formulario.dart';

Future<void> abrirArchivo(BuildContext context, WidgetRef ref, String ruta, String nombre, {String? tipo = 'application/pdf'}) async {
  if (kIsWeb) {
    avisar(context, 'Abra el archivo desde la versión web.');
    return;
  }
  final bytes = await cargarOAvisar(context, ref.read(apiProvider).bytes(ruta));
  if (bytes == null) return;
  final dir = await getTemporaryDirectory();
  final archivo = File('${dir.path}/$nombre');
  await archivo.writeAsBytes(bytes, flush: true);
  final r = await OpenFilex.open(archivo.path, type: tipo);
  if (r.type != ResultType.done && context.mounted) avisar(context, 'No hay una aplicación para abrir este archivo.');
}
