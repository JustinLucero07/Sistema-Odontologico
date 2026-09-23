import { LegalController } from '../../core/services/legal.service';

export interface LegalSection {
  title: string;
  paragraphs: string[];
}

/** Cómo se nombra a la clínica en los textos: razón social si la hay. */
export function controllerName(c: LegalController): string {
  return c.legal_name || c.name;
}

function contactLine(c: LegalController): string {
  const parts = [c.address, c.phone, c.email].filter(Boolean);
  return parts.length ? parts.join(' · ') : 'los datos de contacto de la clínica';
}

/**
 * Aviso de privacidad para pacientes, conforme a la Ley Orgánica de Protección
 * de Datos Personales del Ecuador (LOPDP). Los datos de salud son categoría
 * especial: el texto dice para qué se usan, quién los recibe, cuánto se
 * guardan y cómo ejercer cada derecho.
 */
export function privacyNotice(c: LegalController): LegalSection[] {
  const name = controllerName(c);
  const rightsContact = c.email ? `al correo ${c.email}` : 'en la recepción de la clínica';
  return [
    {
      title: 'Quién trata sus datos',
      paragraphs: [
        `${name}${c.tax_id ? `, RUC ${c.tax_id}` : ''}, es responsable del tratamiento de sus datos personales. ` +
          `Puede contactarnos en ${contactLine(c)}.`,
      ],
    },
    {
      title: 'Qué datos tratamos',
      paragraphs: [
        'Datos de identificación y contacto (nombres, cédula, fecha de nacimiento, teléfono, correo, dirección) ' +
          'y datos de salud: historia clínica, odontograma, diagnósticos, tratamientos, recetas, radiografías ' +
          'e imágenes clínicas, y los pagos asociados a su atención.',
        'Los datos de salud son datos sensibles. Solo acceden a ellos las personas que los necesitan para ' +
          'atenderle, obligadas a guardar secreto profesional, y cada acceso a su historia queda registrado.',
      ],
    },
    {
      title: 'Para qué los usamos',
      paragraphs: [
        'Para prestarle atención odontológica: diagnóstico, tratamiento y seguimiento; llevar su historia ' +
          'clínica como exige la normativa sanitaria; gestionar sus citas; emitir presupuestos, recetas y ' +
          'comprobantes; y cumplir obligaciones legales y tributarias.',
        'Solo si usted lo autoriza, para enviarle recordatorios de citas y otros mensajes por WhatsApp o ' +
          'correo electrónico. Puede retirar esa autorización en cualquier momento, sin que afecte a su atención.',
      ],
    },
    {
      title: 'Con quién los compartimos',
      paragraphs: [
        'Con laboratorios dentales, únicamente lo necesario para confeccionar sus trabajos (prótesis, coronas u ' +
          'otros). Con proveedores de servicios tecnológicos que alojan el sistema, sujetos a contrato y ' +
          'confidencialidad. Y con autoridades cuando una ley lo exija. No vendemos ni cedemos sus datos con ' +
          'fines comerciales.',
      ],
    },
    {
      title: 'Cuánto tiempo los conservamos',
      paragraphs: [
        'La historia clínica se conserva durante el plazo que establece la normativa sanitaria vigente, aun ' +
          'cuando usted deje de ser paciente. Los demás datos, mientras dure la relación y los plazos legales ' +
          'aplicables. Los registros clínicos no se borran ni se sobrescriben: las correcciones quedan anotadas.',
      ],
    },
    {
      title: 'Sus derechos',
      paragraphs: [
        'Puede ejercer sus derechos de acceso, rectificación y actualización, eliminación, oposición, ' +
          'portabilidad y suspensión del tratamiento, y a no ser objeto de decisiones basadas únicamente en ' +
          `tratamientos automatizados. Para hacerlo, escríbanos ${rightsContact}, identificándose con su cédula. ` +
          'Le entregaremos una copia completa de sus datos si la solicita.',
        'La eliminación de la historia clínica está limitada por la obligación legal de conservarla. Si ' +
          'considera que sus derechos no han sido atendidos, puede presentar un reclamo ante la ' +
          'Superintendencia de Protección de Datos Personales.',
      ],
    },
    {
      title: 'Menores de edad',
      paragraphs: [
        'Los datos de niñas, niños y adolescentes se tratan con la autorización de su representante legal, ' +
          'quien ejerce sus derechos en su nombre.',
      ],
    },
  ];
}

/** Acuerdo de confidencialidad que acepta todo el personal con acceso al sistema. */
export function confidentialityAgreement(c: LegalController): LegalSection[] {
  const name = controllerName(c);
  return [
    {
      title: 'Compromiso',
      paragraphs: [
        `Al usar el sistema de ${name}, usted accede a datos personales y de salud de pacientes, que la ley ` +
          'considera sensibles. Se compromete a guardar secreto sobre todo lo que conozca por este medio.',
      ],
    },
    {
      title: 'Qué implica',
      paragraphs: [
        'Acceder solo a la información que necesita para su trabajo, y únicamente con esa finalidad.',
        'No copiar, fotografiar, descargar, reenviar ni comentar datos de pacientes fuera de su función, ni ' +
          'por redes sociales o mensajería personal.',
        'No compartir su usuario ni su contraseña, y cerrar sesión o bloquear el equipo al dejarlo.',
        'Informar de inmediato a la dirección de la clínica cualquier pérdida, acceso indebido o incidente ' +
          'que afecte a los datos.',
      ],
    },
    {
      title: 'Registro y vigencia',
      paragraphs: [
        'Cada acceso a una historia clínica queda registrado con su usuario, fecha y hora.',
        'Este compromiso sigue vigente aun después de que termine su relación con la clínica. Su ' +
          'incumplimiento puede acarrear responsabilidades laborales, civiles y penales.',
      ],
    },
  ];
}
