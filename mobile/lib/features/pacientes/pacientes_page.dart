import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/repositorios.dart';
import '../../core/models/paciente.dart';
import '../../shared/widgets/estado_vacio.dart';
import 'paciente_detalle_page.dart';
import 'pestanas.dart';
import '../../core/auth/auth_controller.dart';
import '../../shared/widgets/boton_flotante.dart';
import '../../shared/widgets/carga.dart';

final busquedaProvider = StateProvider<String>((ref) => '');

final pacientesProvider = FutureProvider.autoDispose<List<PacienteResumen>>((
  ref,
) {
  final termino = ref.watch(busquedaProvider);
  return ref.watch(pacientesRepoProvider).buscar(termino);
});

class PacientesPage extends ConsumerStatefulWidget {
  const PacientesPage({super.key});

  @override
  ConsumerState<PacientesPage> createState() => _PacientesPageState();
}

class _PacientesPageState extends ConsumerState<PacientesPage> {
  final _controlador = TextEditingController();
  Timer? _debounce;

  @override
  void dispose() {
    _debounce?.cancel();
    _controlador.dispose();
    super.dispose();
  }

  void _buscar(String texto) {
    // Sin esta espera, cada tecla lanza una petición; con la clínica llena, el
    // servidor recibe una ráfaga por cada nombre que alguien teclea.
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350), () {
      ref.read(busquedaProvider.notifier).state = texto;
    });
  }

  @override
  Widget build(BuildContext context) {
    final pacientes = ref.watch(pacientesProvider);
    final puedeCrear =
        ref.watch(authProvider).usuario?.puede('patients:write') ?? false;

    return BotonFlotante(
      visible: puedeCrear,
      icono: Icons.person_add_alt,
      texto: 'Nuevo paciente',
      alTocar: () async {
        final id = await editarPaciente(context, ref);
        if (id == null || !context.mounted) return;
        ref.invalidate(pacientesProvider);
        final ficha = await ref.read(pacientesRepoProvider).ficha(id);
        if (!context.mounted) return;
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => PacienteDetallePage(
              pacienteId: id,
              nombre: '${ficha['first_name']} ${ficha['last_name']}',
            ),
          ),
        );
      },
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 10),
            child: TextField(
              controller: _controlador,
              onChanged: _buscar,
              textInputAction: TextInputAction.search,
              decoration: InputDecoration(
                hintText: 'Buscar por nombre o cédula',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _controlador.text.isEmpty
                    ? null
                    : IconButton(
                        icon: const Icon(Icons.clear),
                        tooltip: 'Limpiar',
                        onPressed: () {
                          _controlador.clear();
                          _buscar('');
                          setState(() {});
                        },
                      ),
              ),
            ),
          ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: () async => ref.invalidate(pacientesProvider),
              child: pacientes.when(
                loading: () => const EsqueletoLista(filas: 8),
                error: (e, _) => ListView(
                  children: [
                    EstadoError(
                      mensaje: e is ErrorApi
                          ? e.mensaje
                          : 'Revise la conexión con la clínica.',
                      onReintentar: () => ref.invalidate(pacientesProvider),
                    ),
                  ],
                ),
                data: (lista) {
                  if (lista.isEmpty) {
                    return ListView(
                      children: [
                        EstadoVacio(
                          icono: Icons.person_search,
                          titulo: ref.watch(busquedaProvider).isEmpty
                              ? 'Todavía no hay pacientes'
                              : 'Ningún paciente coincide',
                          detalle: ref.watch(busquedaProvider).isEmpty
                              ? null
                              : 'Pruebe con otro nombre o con la cédula.',
                        ),
                      ],
                    );
                  }
                  return ListView.separated(
                    padding: EdgeInsets.only(
                      bottom: 110 + MediaQuery.paddingOf(context).bottom,
                    ),
                    itemCount: lista.length + (lista.length >= 300 ? 1 : 0),
                    // Lista agrupada: una sola tarjeta blanca con separadores
                    // finos, en vez de filas sueltas sobre el fondo.
                    separatorBuilder: (_, i) => i >= lista.length - 1
                        ? const SizedBox.shrink()
                        : Container(
                            margin: const EdgeInsets.symmetric(horizontal: 16),
                            color: Theme.of(context).colorScheme.surface,
                            child: const Divider(height: 1, indent: 72),
                          ),
                    itemBuilder: (context, i) {
                      // Lista paginada en el servidor: con muchos pacientes se
                      // muestran los primeros 300 y la búsqueda encuentra al resto.
                      if (i == lista.length) {
                        return const Padding(
                          padding: EdgeInsets.all(20),
                          child: Text('Se muestran los primeros 300 por nombre. Use la búsqueda para encontrar al resto.', textAlign: TextAlign.center),
                        );
                      }
                      final p = lista[i];
                      final tono = tonoAvatar(p.id, Theme.of(context).brightness);
                      final radio = Radius.circular(22);
                      return Container(
                        margin: EdgeInsets.fromLTRB(16, i == 0 ? 6 : 0, 16, 0),
                        decoration: BoxDecoration(
                          color: Theme.of(context).colorScheme.surface,
                          borderRadius: BorderRadius.vertical(
                            top: i == 0 ? radio : Radius.zero,
                            bottom: i == lista.length - 1 ? radio : Radius.zero,
                          ),
                        ),
                        clipBehavior: Clip.antiAlias,
                        child: Material(
                          type: MaterialType.transparency,
                          child: ListTile(
                        contentPadding: const EdgeInsets.fromLTRB(14, 4, 10, 4),
                        leading: CircleAvatar(
                          radius: 22,
                          backgroundColor: tono.$1,
                          child: Text(
                            p.iniciales,
                            style: TextStyle(
                              fontSize: 13.5,
                              fontWeight: FontWeight.w700,
                              color: tono.$2,
                            ),
                          ),
                        ),
                        title: Text(
                          p.nombreCompleto,
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                        subtitle: Text(
                          [
                            if (p.edad != null) '${p.edad} años',
                            if (p.cedula != null) 'Cédula ${p.cedula}',
                            if (p.telefono != null) p.telefono!,
                          ].join(' · '),
                        ),
                        trailing: Icon(
                          Icons.arrow_forward_ios_rounded,
                          size: 15,
                          color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.3),
                        ),
                        onTap: () => Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => PacienteDetallePage(
                              pacienteId: p.id,
                              nombre: p.nombreCompleto,
                            ),
                          ),
                        ),
                      ),
                        ),
                      );
                    },
                  );
                },
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Fondo y tinta del avatar de una persona: siempre el mismo tono para el
/// mismo paciente, elegido de una paleta apagada que combina con la marca.
(Color, Color) tonoAvatar(String id, Brightness brillo) {
  const claros = [
    (Color(0xFFE3EFEC), Color(0xFF1F5F57)),
    (Color(0xFFF3EADB), Color(0xFF7A5420)),
    (Color(0xFFE6ECF4), Color(0xFF2E4D74)),
    (Color(0xFFECE7F1), Color(0xFF5A4277)),
    (Color(0xFFEAEFE3), Color(0xFF46602B)),
    (Color(0xFFF2E6E3), Color(0xFF7D3A2F)),
  ];
  const oscuros = [
    (Color(0xFF1C3532), Color(0xFF9FD8CE)),
    (Color(0xFF382D1E), Color(0xFFE5C38F)),
    (Color(0xFF1F2B3B), Color(0xFFA9C3E6)),
    (Color(0xFF2C2537), Color(0xFFCDB8E6)),
    (Color(0xFF26301E), Color(0xFFBCD69B)),
    (Color(0xFF3A2523), Color(0xFFEDB3A9)),
  ];
  final i = id.codeUnits.fold<int>(0, (a, c) => (a * 31 + c) & 0x7fffffff) % claros.length;
  return brillo == Brightness.dark ? oscuros[i] : claros[i];
}
