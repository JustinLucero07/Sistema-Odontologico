import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/repositorios.dart';
import '../../core/models/paciente.dart';
import '../../shared/widgets/estado_vacio.dart';
import 'paciente_detalle_page.dart';

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

    return Column(
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
              loading: () => const Center(child: CircularProgressIndicator()),
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
                    bottom: 24 + MediaQuery.paddingOf(context).bottom,
                  ),
                  itemCount: lista.length,
                  separatorBuilder: (_, __) =>
                      const Divider(height: 1, indent: 72),
                  itemBuilder: (context, i) {
                    final p = lista[i];
                    return ListTile(
                      leading: CircleAvatar(
                        backgroundColor: Theme.of(
                          context,
                        ).colorScheme.primary.withValues(alpha: 0.14),
                        child: Text(
                          p.iniciales,
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: Theme.of(context).colorScheme.primary,
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
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => PacienteDetallePage(
                            pacienteId: p.id,
                            nombre: p.nombreCompleto,
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
    );
  }
}
