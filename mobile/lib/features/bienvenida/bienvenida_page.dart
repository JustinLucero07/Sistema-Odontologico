import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/api/api.dart';
import '../../core/api/repositorios.dart';
import '../../core/auth/auth_controller.dart';
import '../../core/marca/marca.dart';
import '../../shared/widgets/carga.dart';
import '../../shared/widgets/glass.dart';
import '../legal/cumplimiento_page.dart';

const paletaMarca = <(String, int)>[
  ('Verde azulado', 0xFF0D7F76),
  ('Azul clínico', 0xFF1F6FD1),
  ('Índigo', 0xFF4F46E5),
  ('Violeta', 0xFF7B5BD6),
  ('Rosa', 0xFFD0457E),
  ('Coral', 0xFFE0614A),
  ('Ámbar', 0xFFC2851B),
  ('Verde', 0xFF2B8A4B),
  ('Grafito', 0xFF334155),
];

const modulosOpcionales = <(String, String, IconData)>[
  ('opportunities', 'Oportunidades', Icons.tips_and_updates_outlined),
  ('cash', 'Caja del día', Icons.point_of_sale),
  ('credits', 'Créditos', Icons.credit_score),
  ('reports', 'Reportes', Icons.insights),
  ('inventory', 'Inventario', Icons.inventory_2_outlined),
  ('laboratory', 'Laboratorio', Icons.precision_manufacturing_outlined),
];

const _ocultosPorTipo = {
  'independiente': {'inventory', 'laboratory', 'cash', 'messages'},
  'consultorio': {'inventory'},
  'clinica': <String>{},
};

/// Asistente de bienvenida en el celular: el mismo que la web, en pasos
/// cortos para el pulgar. Con [editar] es la pantalla de Personalización.
class BienvenidaPage extends ConsumerStatefulWidget {
  const BienvenidaPage({super.key, this.editar = false});

  final bool editar;

  @override
  ConsumerState<BienvenidaPage> createState() => _BienvenidaPageState();
}

class _BienvenidaPageState extends ConsumerState<BienvenidaPage> {
  final _pagina = PageController();
  int _paso = 0;
  bool _guardando = false;
  String? _error;

  String _tipo = 'independiente';
  final _nombre = TextEditingController();
  final _ruc = TextEditingController();
  final _telefono = TextEditingController();
  final _direccion = TextEditingController();
  final _eslogan = TextEditingController();
  final _registro = TextEditingController();
  final _razon = TextEditingController();
  final _correo = TextEditingController();
  final _pie = TextEditingController();
  bool _atiendo = true;
  bool _acepta = false;
  Color _color = const Color(0xFF0D7F76);
  String? _logo;
  TimeOfDay _abre = const TimeOfDay(hour: 8, minute: 0);
  TimeOfDay _cierra = const TimeOfDay(hour: 18, minute: 0);
  Set<String> _dias = {'1', '2', '3', '4', '5', '6'};
  Set<String> _ocultos = {..._ocultosPorTipo['independiente']!};

  static const _titulos = ['Tu consulta', 'Datos', 'Tu marca', 'Horario', 'Módulos'];

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    try {
      final c = await ref.read(apiProvider).mapa('/clinics/me');
      TimeOfDay hora(String? t, TimeOfDay d) {
        final p = (t ?? '').split(':');
        return p.length == 2 ? TimeOfDay(hour: int.parse(p[0]), minute: int.parse(p[1])) : d;
      }

      final configurada = c['setup_completed_at'] != null;
      // Se configura una sola vez: si ya se hizo en la web (u otro celular),
      // basta con traer la marca y la app sigue a la pantalla principal.
      if (configurada && !widget.editar) {
        await ref.read(marcaProvider.notifier).actualizar();
        return;
      }
      if (!mounted) return;
      setState(() {
        _nombre.text = '${c['name'] ?? ''}';
        _ruc.text = '${c['tax_id'] ?? ''}';
        _telefono.text = '${c['phone'] ?? ''}';
        _direccion.text = '${c['address'] ?? ''}';
        _eslogan.text = '${c['slogan'] ?? ''}';
        _razon.text = '${c['legal_name'] ?? ''}';
        _correo.text = '${c['email'] ?? ''}';
        _pie.text = '${c['document_footer'] ?? ''}';
        _color = colorDeHex(c['primary_color'] as String?) ?? _color;
        _logo = c['logo_data'] as String?;
        _abre = hora(c['opens_at'] as String?, _abre);
        _cierra = hora(c['closes_at'] as String?, _cierra);
        _dias = '${c['work_days'] ?? '123456'}'.split('').toSet();
        if (configurada || widget.editar) {
          _tipo = '${c['practice_type'] ?? 'clinica'}';
          _ocultos = {...((c['hidden_modules'] as List?) ?? []).map((e) => '$e')};
        }
      });
    } catch (_) {}
  }

  @override
  void dispose() {
    for (final c in [_nombre, _ruc, _telefono, _direccion, _eslogan, _registro, _razon, _correo, _pie]) {
      c.dispose();
    }
    _pagina.dispose();
    super.dispose();
  }

  void _ir(int paso) {
    setState(() => _paso = paso);
    _pagina.animateToPage(paso, duration: const Duration(milliseconds: 380), curve: Curves.easeOutCubic);
  }

  bool get _puedeSeguir => switch (_paso) {
    1 => _nombre.text.trim().length >= 2,
    3 => _dias.isNotEmpty,
    4 => widget.editar || _acepta,
    _ => true,
  };

  Future<void> _elegirLogo() async {
    final f = await ImagePicker().pickImage(source: ImageSource.gallery, maxWidth: 512, maxHeight: 512, imageQuality: 90);
    if (f == null) return;
    final bytes = await f.readAsBytes();
    final tipo = f.name.toLowerCase().endsWith('.png') ? 'png' : 'jpeg';
    setState(() => _logo = 'data:image/$tipo;base64,${base64Encode(bytes)}');
  }

  void _verDoc(String codigo) => Navigator.of(context).push(
    MaterialPageRoute<void>(builder: (_) => DocumentoLegalPage(codigo: codigo)),
  );

  String _hhmm(TimeOfDay t) => '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';

  Future<void> _terminar() async {
    setState(() {
      _guardando = true;
      _error = null;
    });
    String? t(TextEditingController c) => c.text.trim().isEmpty ? null : c.text.trim();
    final datos = {
      'name': _nombre.text.trim(),
      'legal_name': t(_razon),
      'email': t(_correo),
      'document_footer': t(_pie),
      'tax_id': _ruc.text.trim().isEmpty ? null : _ruc.text.trim(),
      'phone': _telefono.text.trim().isEmpty ? null : _telefono.text.trim(),
      'address': _direccion.text.trim().isEmpty ? null : _direccion.text.trim(),
      'slogan': _eslogan.text.trim().isEmpty ? null : _eslogan.text.trim(),
      'practice_type': _tipo,
      'primary_color': hexDeColor(_color),
      'logo_data': _logo,
      'opens_at': _hhmm(_abre),
      'closes_at': _hhmm(_cierra),
      'work_days': (_dias.toList()..sort()).join(),
      'hidden_modules': _ocultos.toList(),
    };
    try {
      final api = ref.read(apiProvider);
      if (widget.editar) {
        await api.put('/clinics/me', datos);
      } else {
        await api.post('/clinics/me/setup', {
          ...datos,
          'i_am_dentist': _atiendo,
          'accept_terms': _acepta,
          'license_number': _registro.text.trim().isEmpty ? null : _registro.text.trim(),
        });
      }
      await ref.read(marcaProvider.notifier).actualizar();
      if (mounted && widget.editar) Navigator.of(context).pop();
    } on ErrorApi catch (e) {
      setState(() => _error = e.mensaje);
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final usuario = ref.watch(authProvider).usuario;
    final ultimo = _paso == _titulos.length - 1;
    return AmbientBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: widget.editar
            ? AppBar(flexibleSpace: const GlassAppBarBackground(), title: const Text('Personalización'))
            : null,
        body: SafeArea(
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
                child: Row(
                  children: [
                    for (var i = 0; i < _titulos.length; i++)
                      Expanded(
                        child: AnimatedContainer(
                          duration: const Duration(milliseconds: 300),
                          height: 5,
                          margin: EdgeInsets.only(right: i < _titulos.length - 1 ? 6 : 0),
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(3),
                            color: i <= _paso ? _color : scheme.onSurface.withValues(alpha: 0.12),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    'Paso ${_paso + 1} de ${_titulos.length} · ${_titulos[_paso]}',
                    style: TextStyle(fontSize: 12.5, color: scheme.onSurface.withValues(alpha: 0.55), fontWeight: FontWeight.w600),
                  ),
                ),
              ),
              Expanded(
                child: PageView(
                  controller: _pagina,
                  physics: const NeverScrollableScrollPhysics(),
                  children: [
                    _pasoTipo(usuario?.nombre),
                    _pasoDatos(),
                    _pasoMarca(),
                    _pasoHorario(),
                    _pasoModulos(),
                  ],
                ),
              ),
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  child: Text(_error!, style: TextStyle(color: scheme.error)),
                ),
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 16),
                child: Row(
                  children: [
                    if (_paso > 0)
                      OutlinedButton.icon(
                        style: OutlinedButton.styleFrom(minimumSize: const Size(0, 52), shape: const StadiumBorder()),
                        onPressed: () => _ir(_paso - 1),
                        icon: const Icon(Icons.arrow_back),
                        label: const Text('Atrás'),
                      ),
                    if (_paso > 0) const SizedBox(width: 10),
                    Expanded(
                      child: FilledButton(
                        style: FilledButton.styleFrom(backgroundColor: _color),
                        onPressed: !_puedeSeguir || _guardando
                            ? null
                            : () => ultimo ? _terminar() : _ir(_paso + 1),
                        child: Text(
                          _guardando
                              ? 'Guardando…'
                              : ultimo
                              ? (widget.editar ? 'Guardar cambios' : 'Empezar a usar el sistema')
                              : 'Continuar',
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _marco({required String titulo, String? sub, required List<Widget> hijos}) {
    final scheme = Theme.of(context).colorScheme;
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
      children: [
        Text(titulo, style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w800, letterSpacing: -0.8)),
        if (sub != null)
          Padding(
            padding: const EdgeInsets.only(top: 4, bottom: 18),
            child: Text(sub, style: TextStyle(color: scheme.onSurface.withValues(alpha: 0.6), height: 1.4)),
          ),
        ...hijos,
      ],
    );
  }

  Widget _pasoTipo(String? nombre) {
    Widget tarjeta(String v, IconData i, String t, String d) {
      final on = _tipo == v;
      return Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(22),
            border: Border.all(color: on ? _color : Colors.transparent, width: 2),
          ),
          child: GlassCard(
            onTap: () => setState(() {
              _tipo = v;
              if (!widget.editar) _ocultos = {..._ocultosPorTipo[v]!};
              _atiendo = v != 'clinica';
            }),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Container(
                    width: 50,
                    height: 50,
                    decoration: BoxDecoration(color: _color, borderRadius: BorderRadius.circular(16)),
                    child: Icon(i, color: Colors.white),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(t, style: const TextStyle(fontSize: 16.5, fontWeight: FontWeight.w700)),
                        const SizedBox(height: 2),
                        Text(d, style: const TextStyle(fontSize: 13, height: 1.35)),
                      ],
                    ),
                  ),
                  if (on) Icon(Icons.check_circle, color: _color),
                ],
              ),
            ),
          ),
        ),
      );
    }

    return _marco(
      titulo: widget.editar ? 'Tipo de consulta' : '¡Bienvenido${nombre != null ? ', $nombre' : ''}!',
      sub: '¿Cómo trabajas? Así mostramos solo lo que necesitas.',
      hijos: [
        tarjeta('independiente', Icons.person, 'Trabajo solo', 'Odontólogo independiente. Agenda, fichas y cobros sin complicaciones.'),
        tarjeta('consultorio', Icons.group, 'Consultorio pequeño', 'Dos o tres odontólogos, cada uno con su agenda.'),
        tarjeta('clinica', Icons.local_hospital, 'Clínica con equipo', 'Recepción, varios sillones, caja, inventario y laboratorio.'),
      ],
    );
  }

  Widget _pasoDatos() {
    InputDecoration d(String l, [String? h]) => InputDecoration(labelText: l, hintText: h);
    return _marco(
      titulo: 'Datos de tu consulta',
      sub: 'Aparecen en recetas, recibos y certificados.',
      hijos: [
        TextField(controller: _nombre, decoration: d('Nombre comercial *', 'Ej. Consultorio Dra. Ana Paz'), onChanged: (_) => setState(() {})),
        const SizedBox(height: 12),
        TextField(controller: _razon, decoration: d('Razón social', 'Si es distinta del nombre comercial')),
        const SizedBox(height: 12),
        TextField(controller: _ruc, keyboardType: TextInputType.number, decoration: d('RUC')),
        const SizedBox(height: 12),
        TextField(controller: _correo, keyboardType: TextInputType.emailAddress, autocorrect: false, decoration: d('Correo')),
        const SizedBox(height: 12),
        TextField(controller: _telefono, keyboardType: TextInputType.phone, decoration: d('Teléfono / WhatsApp')),
        const SizedBox(height: 12),
        TextField(controller: _direccion, decoration: d('Dirección')),
        const SizedBox(height: 12),
        TextField(controller: _eslogan, decoration: d('Eslogan (opcional)', 'Tu sonrisa en buenas manos')),
        if (!widget.editar) ...[
          const SizedBox(height: 16),
          GlassCard(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                children: [
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    value: _atiendo,
                    onChanged: (v) => setState(() => _atiendo = v),
                    title: const Text('Yo también atiendo pacientes'),
                    subtitle: const Text('Te registramos como profesional para agendar y firmar recetas.'),
                  ),
                  if (_atiendo) TextField(controller: _registro, decoration: d('Registro profesional', 'Ej. MSP 1234-5678')),
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }

  Widget _pasoMarca() {
    final bytes = bytesDeLogo(_logo);
    return _marco(
      titulo: 'Tu marca',
      sub: 'Tu logo y tu color en toda la app y en los documentos.',
      hijos: [
        GlassCard(
          onTap: _elegirLogo,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Container(
                  width: 68,
                  height: 68,
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(18)),
                  child: bytes != null
                      ? Image.memory(bytes, fit: BoxFit.contain)
                      : Icon(Icons.add_photo_alternate_outlined, color: _color, size: 34),
                ),
                const SizedBox(width: 14),
                Expanded(child: Text(bytes != null ? 'Cambiar logo' : 'Subir logo desde la galería', style: const TextStyle(fontWeight: FontWeight.w700))),
                if (bytes != null)
                  IconButton(onPressed: () => setState(() => _logo = null), icon: const Icon(Icons.delete_outline)),
              ],
            ),
          ),
        ),
        const SizedBox(height: 20),
        const Text('Color principal', style: TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(height: 10),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            for (final (nombre, hex) in paletaMarca)
              Tooltip(
                message: nombre,
                child: GestureDetector(
                  onTap: () => setState(() => _color = Color(hex)),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 180),
                    width: 50,
                    height: 50,
                    decoration: BoxDecoration(
                      color: Color(hex),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: _color.toARGB32() == hex ? Colors.white : Colors.transparent, width: 3),
                      boxShadow: _color.toARGB32() == hex ? [BoxShadow(color: Color(hex), blurRadius: 0, spreadRadius: 2)] : null,
                    ),
                    child: _color.toARGB32() == hex ? const Icon(Icons.check, color: Colors.white) : null,
                  ),
                ),
              ),
          ],
        ),
        const SizedBox(height: 18),
        TextField(
          controller: _pie,
          maxLines: 2,
          decoration: const InputDecoration(labelText: 'Pie de recibos y certificados (opcional)', hintText: 'Gracias por su confianza'),
        ),
        const SizedBox(height: 22),
        // Vista previa
        Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(22),
            gradient: LinearGradient(colors: [tono(_color, -0.3), _color]),
          ),
          child: Row(
            children: [
              Container(
                width: 46,
                height: 46,
                padding: const EdgeInsets.all(4),
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
                child: bytes != null ? Image.memory(bytes) : Icon(Icons.medical_services, color: _color),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(_nombre.text.isEmpty ? 'Tu consultorio' : _nombre.text,
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 16)),
                    Text(_eslogan.text.isEmpty ? 'Así se verá tu app' : _eslogan.text,
                        style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 12.5)),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _pasoHorario() {
    const dias = [('1', 'L'), ('2', 'M'), ('3', 'X'), ('4', 'J'), ('5', 'V'), ('6', 'S'), ('7', 'D')];
    Future<void> hora(bool abre) async {
      final t = await showTimePicker(context: context, initialTime: abre ? _abre : _cierra);
      if (t != null) setState(() => abre ? _abre = t : _cierra = t);
    }

    return _marco(
      titulo: 'Horario de atención',
      sub: 'Lo usamos para sugerirte huecos libres en la agenda.',
      hijos: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            for (final (n, l) in dias)
              GestureDetector(
                onTap: () => setState(() => _dias.contains(n) ? _dias.remove(n) : _dias.add(n)),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 180),
                  width: 42,
                  height: 42,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: _dias.contains(n) ? _color : Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.07),
                  ),
                  child: Text(l, style: TextStyle(fontWeight: FontWeight.w700, color: _dias.contains(n) ? Colors.white : null)),
                ),
              ),
          ],
        ),
        const SizedBox(height: 22),
        Row(
          children: [
            Expanded(child: _botonHora('Abre', _abre, () => hora(true))),
            const SizedBox(width: 12),
            Expanded(child: _botonHora('Cierra', _cierra, () => hora(false))),
          ],
        ),
      ],
    );
  }

  Widget _botonHora(String etiqueta, TimeOfDay t, VoidCallback alTocar) => GlassCard(
    onTap: alTocar,
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          Text(etiqueta, style: const TextStyle(fontSize: 12.5)),
          const SizedBox(height: 4),
          Text(_hhmm(t), style: TextStyle(fontSize: 26, fontWeight: FontWeight.w800, color: _color)),
        ],
      ),
    ),
  );

  Widget _pasoModulos() {
    return _marco(
      titulo: '¿Qué quieres ver?',
      sub: 'Agenda, pacientes y finanzas siempre están. Lo demás lo activas cuando quieras.',
      hijos: [
        for (final (codigo, nombre, icono) in modulosOpcionales)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: GlassCard(
              child: SwitchListTile(
                value: !_ocultos.contains(codigo),
                activeThumbColor: _color,
                onChanged: (v) => setState(() => v ? _ocultos.remove(codigo) : _ocultos.add(codigo)),
                secondary: Icon(icono, color: _ocultos.contains(codigo) ? null : _color),
                title: Text(nombre, style: const TextStyle(fontWeight: FontWeight.w600)),
              ),
            ),
          ),
        if (!widget.editar) ...[
          const SizedBox(height: 10),
          GlassCard(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(4, 8, 12, 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  CheckboxListTile(
                    value: _acepta,
                    activeColor: _color,
                    controlAffinity: ListTileControlAffinity.leading,
                    onChanged: (v) => setState(() => _acepta = v ?? false),
                    title: const Text('Acepto los Términos de uso y el Contrato de encargo de tratamiento de datos'),
                  ),
                  Wrap(
                    spacing: 4,
                    children: [
                      TextButton(onPressed: () => _verDoc('terminos'), child: const Text('Leer Términos')),
                      TextButton(onPressed: () => _verDoc('encargo'), child: const Text('Leer Contrato')),
                    ],
                  ),
                  const Padding(
                    padding: EdgeInsets.only(left: 12),
                    child: Text(
                      'Tus pacientes y sus historias son tuyos. La aceptación queda registrada con tu nombre y la fecha.',
                      style: TextStyle(fontSize: 12.5),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }
}

/// Logo de la consulta (o el diente por defecto) para usar en cualquier sitio.
class LogoConsulta extends ConsumerWidget {
  const LogoConsulta({super.key, this.tamano = 30});

  final double tamano;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(marcaProvider);
    return LogoApp(tamano: tamano);
  }
}
