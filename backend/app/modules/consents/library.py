"""Biblioteca de consentimientos informados odontológicos.

Son una base de partida redactada para el contexto ecuatoriano (Ley Orgánica
de Salud, Ley Orgánica de Protección de Datos Personales). Cada consulta debe
revisarlas con su profesional responsable y ajustarlas a su práctica antes de
usarlas: el sistema las copia como plantillas editables, no las impone.

Variables que se completan al emitir el consentimiento para un paciente:
{paciente} {cedula} {edad} {fecha} {ciudad} {clinica} {profesional}
{registro} {pieza} {procedimiento}
"""

ENCABEZADO = (
    "Yo, {paciente}, con cédula {cedula}, de {edad}, en pleno uso de mis facultades, declaro que "
    "el/la profesional {profesional} (registro {registro}) de {clinica} me ha explicado de forma "
    "clara y en lenguaje comprensible lo siguiente sobre el procedimiento: {procedimiento}.\n\n"
)

CIERRE = (
    "\n\nHe podido hacer todas las preguntas que consideré necesarias y han sido respondidas a mi "
    "satisfacción. Entiendo que puedo revocar este consentimiento en cualquier momento antes del "
    "procedimiento, sin que ello afecte la atención que recibo. Declaro que la información que he "
    "proporcionado sobre mi salud (enfermedades, alergias, medicamentos, embarazo) es verdadera.\n\n"
    "En consecuencia, AUTORIZO la realización del procedimiento descrito.\n\n"
    "{ciudad}, {fecha}."
)


def _texto(cuerpo: str) -> str:
    return ENCABEZADO + cuerpo.strip() + CIERRE


BIBLIOTECA: list[tuple[str, str, str]] = [
    (
        "Atención odontológica general y tratamiento de datos",
        "general",
        "Yo, {paciente}, con cédula {cedula}, autorizo a {clinica} a realizar la valoración, el "
        "diagnóstico y los tratamientos odontológicos básicos (examen clínico, limpieza, profilaxis, "
        "aplicación de flúor y sellantes, restauraciones simples) que el/la profesional considere "
        "necesarios, previa explicación de cada uno.\n\n"
        "TRATAMIENTO DE MIS DATOS PERSONALES: conforme a la Ley Orgánica de Protección de Datos "
        "Personales, autorizo a {clinica} a registrar y conservar mis datos de identificación, de "
        "contacto y de salud (historia clínica, odontograma, radiografías y fotografías clínicas) con "
        "la finalidad de prestarme atención odontológica, gestionar mis citas, cobros y facturación, y "
        "enviarme recordatorios. Sé que mis datos de salud son datos sensibles, que serán tratados de "
        "forma confidencial, que se conservarán el tiempo que exige la normativa de historias clínicas, "
        "y que puedo ejercer mis derechos de acceso, rectificación, eliminación, oposición y "
        "portabilidad solicitándolo a la consulta.\n\n"
        "Autorizo / no autorizo (tache lo que no corresponda) el envío de recordatorios de citas por "
        "WhatsApp y correo electrónico.\n\n"
        "{ciudad}, {fecha}.",
    ),
    (
        "Anestesia local",
        "anestesia",
        _texto(
            "EN QUÉ CONSISTE: aplicar un anestésico mediante una inyección en la encía o el paladar para "
            "que el procedimiento no cause dolor. El efecto dura entre 1 y 4 horas.\n\n"
            "RIESGOS Y MOLESTIAS POSIBLES: dolor o hematoma en el lugar de la inyección; sensación de "
            "adormecimiento prolongado del labio, la lengua o la mejilla, que rara vez puede durar "
            "semanas; mordedura accidental de labio o lengua mientras dura el efecto; palpitaciones o "
            "mareo pasajeros; muy rara vez, reacción alérgica.\n\n"
            "MIS COMPROMISOS: informar si tengo alergias, problemas cardíacos, presión alta, embarazo o "
            "si tomo medicamentos; no comer ni masticar hasta que pase el efecto; vigilar a los niños "
            "para que no se muerdan."
        ),
    ),
    (
        "Exodoncia (extracción dental)",
        "exodoncia",
        _texto(
            "EN QUÉ CONSISTE: extraer la pieza {pieza} bajo anestesia local, porque no puede conservarse "
            "o porque su permanencia perjudica la salud bucal.\n\n"
            "ALTERNATIVAS: según el caso, tratamiento de conductos, restauración o no tratar (con el "
            "riesgo de infección, dolor y daño a piezas vecinas).\n\n"
            "RIESGOS POSIBLES: dolor, inflamación y hematoma los primeros días; sangrado; infección o "
            "alveolitis (dolor intenso varios días después); fractura de la raíz que obligue a una "
            "cirugía; daño a una restauración o pieza vecina; en extracciones superiores, comunicación "
            "con el seno maxilar; adormecimiento temporal del labio o la lengua.\n\n"
            "CUIDADOS POSTERIORES: morder la gasa 30 a 40 minutos; no escupir, no enjuagar ni fumar las "
            "primeras 24 horas; dieta blanda y fría; tomar la medicación indicada; acudir si el sangrado "
            "o el dolor no ceden."
        ),
    ),
    (
        "Cirugía de terceros molares (muelas del juicio)",
        "cirugia",
        _texto(
            "EN QUÉ CONSISTE: extracción quirúrgica de la(s) pieza(s) {pieza}, que puede requerir abrir "
            "la encía, retirar hueso y dividir la pieza, con puntos de sutura.\n\n"
            "RIESGOS POSIBLES: inflamación importante y dificultad para abrir la boca durante varios "
            "días; dolor; hematomas en la cara; sangrado; infección o alveolitis; lesión de nervios que "
            "puede causar adormecimiento del labio, el mentón o la lengua, generalmente temporal y rara "
            "vez permanente; comunicación con el seno maxilar en piezas superiores; daño a la pieza "
            "vecina; excepcionalmente fractura mandibular.\n\n"
            "CUIDADOS POSTERIORES: frío local las primeras 48 horas, reposo, dieta blanda, medicación "
            "indicada, higiene cuidadosa y control para retirar los puntos."
        ),
    ),
    (
        "Endodoncia (tratamiento de conductos)",
        "endodoncia",
        _texto(
            "EN QUÉ CONSISTE: retirar el nervio (pulpa) inflamado o infectado de la pieza {pieza}, "
            "limpiar y desinfectar sus conductos y sellarlos, en una o varias citas, con radiografías "
            "de control.\n\n"
            "ALTERNATIVAS: la extracción de la pieza.\n\n"
            "RIESGOS POSIBLES: molestias o dolor al masticar unos días; reagudización de la infección; "
            "fractura de un instrumento dentro del conducto; perforación de la raíz; conductos muy "
            "calcificados o curvos que impidan terminar el tratamiento; fracaso con necesidad de "
            "retratamiento, cirugía o extracción.\n\n"
            "IMPORTANTE: la pieza tratada queda más frágil y suele necesitar una restauración definitiva "
            "o corona; no colocarla a tiempo puede provocar su fractura o pérdida."
        ),
    ),
    (
        "Implantes dentales",
        "implantes",
        _texto(
            "EN QUÉ CONSISTE: colocar en el hueso uno o varios implantes de titanio en la zona {pieza} "
            "para reemplazar piezas perdidas. Tras un tiempo de integración (habitualmente 3 a 6 meses) "
            "se coloca la corona o prótesis. Puede requerir injerto de hueso o elevación de seno.\n\n"
            "ALTERNATIVAS: prótesis fija sobre dientes vecinos, prótesis removible o no reponer la pieza.\n\n"
            "RIESGOS POSIBLES: dolor, inflamación y hematomas; infección; que el implante no se integre "
            "y deba retirarse; lesión de nervios con adormecimiento temporal o, rara vez, permanente; "
            "comunicación con el seno maxilar; pérdida de hueso alrededor del implante (periimplantitis) "
            "con el tiempo.\n\n"
            "FACTORES QUE AUMENTAN EL RIESGO: tabaco, diabetes no controlada, mala higiene, "
            "bruxismo y algunos medicamentos para los huesos. MIS COMPROMISOS: higiene rigurosa y "
            "controles periódicos."
        ),
    ),
    (
        "Ortodoncia",
        "ortodoncia",
        _texto(
            "EN QUÉ CONSISTE: corregir la posición de los dientes y la mordida con aparatos fijos "
            "(brackets) o removibles/alineadores, durante un tiempo estimado que puede variar según la "
            "respuesta de cada paciente y su colaboración.\n\n"
            "RIESGOS POSIBLES: molestias y llagas al inicio y tras cada ajuste; descalcificaciones o "
            "caries si la higiene es deficiente; inflamación de encías; acortamiento de raíces; "
            "molestias en la articulación de la mandíbula; recidiva (los dientes tienden a volver a su "
            "posición) si no se usan los retenedores indicados.\n\n"
            "MIS COMPROMISOS: asistir a los controles, mantener una higiene estricta, cuidar los "
            "aparatos, usar elásticos y retenedores como se indique. La falta de colaboración puede "
            "prolongar el tratamiento o impedir el resultado esperado."
        ),
    ),
    (
        "Blanqueamiento dental",
        "blanqueamiento",
        _texto(
            "EN QUÉ CONSISTE: aclarar el color de los dientes con un gel blanqueador aplicado en la "
            "consulta y/o en casa con férulas, según el plan indicado.\n\n"
            "ES UN PROCEDIMIENTO ESTÉTICO: el resultado varía en cada persona y no puede garantizarse "
            "un tono específico. Las restauraciones, carillas y coronas no cambian de color y podrían "
            "necesitar reemplazo para igualar el tono.\n\n"
            "RIESGOS POSIBLES: sensibilidad dental durante el tratamiento y unos días después; "
            "irritación de encías; manchas temporales; el color tiende a oscurecer con el tiempo, "
            "sobre todo con café, té, vino o tabaco.\n\n"
            "NO SE RECOMIENDA en embarazo o lactancia, ni con caries o enfermedad de encías sin tratar."
        ),
    ),
    (
        "Tratamiento periodontal",
        "periodoncia",
        _texto(
            "EN QUÉ CONSISTE: tratar la enfermedad de las encías y del hueso que sostiene los dientes "
            "mediante raspado y alisado radicular bajo anestesia local y, si fuera necesario, cirugía "
            "periodontal, seguidos de controles de mantenimiento.\n\n"
            "RIESGOS POSIBLES: sensibilidad al frío; encías que se retraen y dejan los dientes más "
            "largos o con espacios; molestias y sangrado leve; movilidad dental temporal; en "
            "enfermedad avanzada, pérdida de piezas a pesar del tratamiento.\n\n"
            "MIS COMPROMISOS: higiene diaria según lo enseñado, dejar o reducir el tabaco y acudir a "
            "las citas de mantenimiento, sin las cuales la enfermedad suele volver."
        ),
    ),
    (
        "Prótesis dental (fija o removible)",
        "protesis",
        _texto(
            "EN QUÉ CONSISTE: reponer piezas perdidas o muy dañadas ({pieza}) con coronas, puentes o "
            "prótesis removibles, lo que puede requerir tallar dientes, tomar impresiones y varias "
            "pruebas.\n\n"
            "RIESGOS POSIBLES: sensibilidad o necesidad de tratamiento de conductos en dientes "
            "tallados; periodo de adaptación para hablar y masticar; llagas por roce que requieren "
            "ajustes; fractura de la porcelana o del material; descementado.\n\n"
            "IMPORTANTE: la duración de la prótesis depende de la higiene, los controles y los hábitos "
            "(bruxismo, morder objetos duros)."
        ),
    ),
    (
        "Atención odontológica a menores de edad",
        "odontopediatria",
        "Yo, en mi calidad de representante legal (madre, padre o tutor) del/de la menor {paciente}, "
        "con cédula {cedula}, de {edad}, declaro que el/la profesional {profesional} (registro "
        "{registro}) de {clinica} me ha explicado el procedimiento: {procedimiento}, sus beneficios, "
        "riesgos y alternativas.\n\n"
        "Entiendo que durante la atención pueden ser necesarias técnicas para guiar la conducta del "
        "niño o niña (explicar-mostrar-hacer, refuerzo positivo) y que, si no colabora, el tratamiento "
        "podría reprogramarse o derivarse. Me comprometo a acompañarlo/a, a informar sobre su salud, "
        "alergias y medicamentos, y a seguir las indicaciones posteriores.\n\n"
        "AUTORIZO la atención odontológica del/de la menor.\n\n{ciudad}, {fecha}.",
    ),
    (
        "Radiografías y fotografías clínicas",
        "imagenes",
        _texto(
            "EN QUÉ CONSISTE: tomar radiografías (periapicales, panorámicas u otras) y fotografías de "
            "la boca y el rostro para diagnosticar, planificar y controlar el tratamiento.\n\n"
            "RADIACIÓN: la dosis de una radiografía dental es muy baja; se usan las protecciones "
            "adecuadas. Debo informar si estoy o podría estar embarazada.\n\n"
            "USO DE LAS IMÁGENES: forman parte de mi historia clínica y son confidenciales. "
            "Autorizo / no autorizo (tache lo que no corresponda) su uso con fines docentes o "
            "científicos sin que se me pueda identificar, y autorizo / no autorizo su uso en "
            "publicaciones o redes de la consulta."
        ),
    ),
]
