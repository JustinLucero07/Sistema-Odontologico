/// Siluetas dentales anatómicas.
///
/// **Generado desde `frontend/src/app/shared/odontogram/tooth-anatomy.ts`.**
/// Los trazados se copian literalmente en lugar de redibujarse: si la web y la
/// app dibujasen dientes distintos, el mismo paciente tendría dos odontogramas
/// que no se parecen.
///
/// Caja canónica de 40 × 64, con la corona ABAJO (y ≈ 36–60) y las raíces
/// arriba (y ≈ 2–37), es decir una pieza del maxilar superior. Las inferiores
/// reutilizan el mismo trazado volteado en vertical, que es como los odonto-
/// gramas impresos reflejan las dos arcadas alrededor de la línea media.
library;

class ToothAnatomy {
  const ToothAnatomy({
    required this.roots,
    required this.crown,
    required this.detail,
    required this.gloss,
    required this.shade,
    required this.width,
  });

  final List<String> roots;
  final String crown;

  /// Accidentes anatómicos trazados: la unión amelocementaria y los surcos
  /// entre cúspides. Líneas de pelo: se ven al mirar, no molestan al no mirar.
  final List<String> detail;

  /// Brillo por la pared mesial.
  final String gloss;

  /// Sombra por la pared distal. Esto es lo que da volumen: se lee igual sobre
  /// un diente blanco que sobre uno relleno, cosa que el brillo solo no hace.
  final String shade;

  /// Ancho de la celda: un molar de verdad es más ancho que un incisivo.
  final int width;
}

const Map<String, ToothAnatomy> anatomias = {
  'incisor': ToothAnatomy(
    roots: [
      'M 15.05 36.5 C 15.3 27 16.3 12 18.6 4.2 C 19.2 2.1 20.8 2.1 21.4 4.2 C 23.7 12 24.7 27 24.95 36.5 Z',
    ],
    crown:
        'M 15 36 C 13.7 41.5 12.6 47.5 12.6 53 C 12.6 57.2 13.5 59.4 15.6 59.5 L 24.4 59.5 C 26.5 59.4 27.4 57.2 27.4 53 C 27.4 47.5 26.3 41.5 25 36 Z',
    detail: [
      'M 15.2 37.4 C 18 38.7 22 38.7 24.8 37.4',
      'M 14 55.8 C 17.6 57 22.4 57 26 55.8',
      'M 17.2 56.4 L 17.2 59.4',
      'M 22.8 56.4 L 22.8 59.4',
    ],
    gloss: 'M 14.4 42.4 C 13.8 46.6 13.6 51 13.7 54.6',
    shade: 'M 25.6 42.4 C 26.2 46.6 26.4 51 26.3 54.6',
    width: 30,
  ),
  'canine': ToothAnatomy(
    roots: [
      'M 14.85 36.5 C 15.1 26 15.9 10.5 18.4 2.4 C 19.1 0.4 20.9 0.4 21.6 2.4 C 24.1 10.5 24.9 26 25.15 36.5 Z',
    ],
    crown:
        'M 14.8 36 C 13.3 41.6 12 48 12 52.4 C 12 56.2 15.6 59.6 20 63.4 C 24.4 59.6 28 56.2 28 52.4 C 28 48 26.7 41.6 25.2 36 Z',
    detail: [
      'M 15 37.4 C 18 38.8 22 38.8 25 37.4',
      'M 14.6 53.4 L 20 59.6 L 25.4 53.4',
    ],
    gloss: 'M 13.9 42.4 C 13.2 46.8 13 51 13.4 54',
    shade: 'M 26.1 42.4 C 26.8 46.8 27 51 26.6 54',
    width: 31,
  ),
  'premolar': ToothAnatomy(
    roots: [
      'M 14.05 36.5 C 14.3 27 15.3 11.5 18.2 3.6 C 19 1.6 21 1.6 21.8 3.6 C 24.7 11.5 25.7 27 25.95 36.5 Z',
    ],
    crown:
        'M 14 36 C 12.3 41.6 11 48 11 52.2 C 11 56 13 59.4 15.6 59.5 C 17.6 59.6 18.8 57.2 19.4 55 C 19.6 54 20.4 54 20.6 55 C 21.2 57.2 22.4 59.6 24.4 59.5 C 27 59.4 29 56 29 52.2 C 29 48 27.7 41.6 26 36 Z',
    detail: ['M 14.3 37.4 C 17.6 38.9 22.4 38.9 25.7 37.4', 'M 20 48 L 20 54'],
    gloss: 'M 12.8 42.4 C 12.1 46.8 12 51.4 12.2 54.8',
    shade: 'M 27.2 42.4 C 27.9 46.8 28 51.4 27.8 54.8',
    width: 35,
  ),
  'molar_upper': ToothAnatomy(
    roots: [
      'M 8.55 36.5 C 7.7 28 6 15.5 4.7 7.2 C 4.3 4.8 6 4.2 6.9 6.2 C 9.7 14 13 25.5 14.5 36.5 Z',
      'M 17 36.5 C 17.2 28 17.8 13 18.7 5.2 C 19.1 3 20.9 3 21.3 5.2 C 22.2 13 22.8 28 23 36.5 Z',
      'M 31.45 36.5 C 32.3 28 34 15.5 35.3 7.2 C 35.7 4.8 34 4.2 33.1 6.2 C 30.3 14 27 25.5 25.5 36.5 Z',
    ],
    crown:
        'M 8.5 36 C 6.6 41.6 5 48 5 52.2 C 5 56 7.6 59.4 10.4 59.5 C 12.8 59.6 14 57.4 14.7 55 C 15 54 16 54 16.3 55 C 16.9 57 18.1 58.2 20 58.2 C 21.9 58.2 23.1 57 23.7 55 C 24 54 25 54 25.3 55 C 26 57.4 27.2 59.6 29.6 59.5 C 32.4 59.4 35 56 35 52.2 C 35 48 33.4 41.6 31.5 36 Z',
    detail: [
      'M 8.8 37.4 C 15.4 39.4 24.6 39.4 31.2 37.4',
      'M 15.5 49 L 15.5 54.2',
      'M 20 47.6 L 20 57.6',
      'M 24.5 49 L 24.5 54.2',
    ],
    gloss: 'M 7 42.4 C 6.3 46.8 6.2 51.4 6.4 54.8',
    shade: 'M 33 42.4 C 33.7 46.8 33.8 51.4 33.6 54.8',
    width: 46,
  ),
  'molar_lower': ToothAnatomy(
    roots: [
      'M 8.55 36.5 C 7.9 28 6.7 15.2 5.9 6.8 C 5.6 4.4 7.5 3.8 8.5 6 C 11.5 13.6 14.5 25.5 16 36.5 Z',
      'M 31.45 36.5 C 32.1 28 33.3 15.2 34.1 6.8 C 34.4 4.4 32.5 3.8 31.5 6 C 28.5 13.6 25.5 25.5 24 36.5 Z',
    ],
    crown:
        'M 8.5 36 C 6.6 41.6 5 48 5 52.2 C 5 56 7.6 59.4 10.4 59.5 C 12.8 59.6 14 57.4 14.7 55 C 15 54 16 54 16.3 55 C 16.9 57 18.1 58.2 20 58.2 C 21.9 58.2 23.1 57 23.7 55 C 24 54 25 54 25.3 55 C 26 57.4 27.2 59.6 29.6 59.5 C 32.4 59.4 35 56 35 52.2 C 35 48 33.4 41.6 31.5 36 Z',
    detail: [
      'M 8.8 37.4 C 15.4 39.4 24.6 39.4 31.2 37.4',
      'M 15.5 49 L 15.5 54.2',
      'M 20 47.6 L 20 57.6',
      'M 24.5 49 L 24.5 54.2',
    ],
    gloss: 'M 7 42.4 C 6.3 46.8 6.2 51.4 6.4 54.8',
    shade: 'M 33 42.4 C 33.7 46.8 33.8 51.4 33.6 54.8',
    width: 46,
  ),
};

String tipoDeDiente(String fdi) {
  final cuadrante = int.parse(fdi[0]);
  final posicion = int.parse(fdi[1]);
  final temporal = cuadrante >= 5;

  if (posicion <= 2) return 'incisor';
  if (posicion == 3) return 'canine';
  // La dentición temporal no tiene premolares: las posiciones 4–5 son molares.
  if (temporal) return 'molar';
  return posicion <= 5 ? 'premolar' : 'molar';
}

/// Escala del dibujo respecto a los anchos base.
const double escalaGrafico = 1.15;

/// Multiplicadores por posición FDI. Los dientes no son intercambiables dentro
/// de su tipo: el lateral superior es más angosto que el central, el central
/// INFERIOR es el diente más pequeño de la boca, y los terceros molares
/// encogen.
double _escalaAncho(String fdi, String arcada) {
  final posicion = int.parse(fdi[1]);
  if (posicion == 1) return arcada == 'upper' ? 1 : 0.8;
  if (posicion == 2) return arcada == 'upper' ? 0.87 : 0.88;
  if (posicion == 7) return 0.95;
  if (posicion == 8) return 0.87;
  return 1;
}

ToothAnatomy anatomiaDe(String fdi, String arcada) {
  final tipo = tipoDeDiente(fdi);
  final clave = tipo == 'molar'
      ? (arcada == 'upper' ? 'molar_upper' : 'molar_lower')
      : tipo;
  final base = anatomias[clave]!;
  final escala = _escalaAncho(fdi, arcada) * escalaGrafico;
  return ToothAnatomy(
    roots: base.roots,
    crown: base.crown,
    detail: base.detail,
    gloss: base.gloss,
    shade: base.shade,
    width: (base.width * escala).round(),
  );
}
