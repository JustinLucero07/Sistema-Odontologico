export type ClinicalImageType =
  | 'panoramica'
  | 'periapical'
  | 'bitewing'
  | 'lateral'
  | 'oclusal'
  | 'tomografia'
  | 'foto_intraoral'
  | 'foto_extraoral'
  | 'otro';

export interface ClinicalImage {
  id: string;
  patient_id: string;
  professional_id: string | null;
  uploaded_by_id: string | null;
  created_at: string;
  image_type: ClinicalImageType;
  title: string;
  description: string | null;
  /** When the study was TAKEN — an old radiograph scanned today still sorts
   *  by its own date, not by the upload. */
  taken_on: string | null;
  fdi_numbers: string[] | null;
  original_filename: string;
  mime_type: string | null;
  size_bytes: number | null;
  width: number | null;
  height: number | null;
  archived_at: string | null;
  archived_reason: string | null;
}

export interface ClinicalImageTypeOption {
  code: ClinicalImageType;
  label: string;
  /** Radiographs read tooth by tooth: the form asks which pieces are in frame. */
  tooth_scoped: boolean;
}

export const IMAGE_TYPE_ICONS: Record<ClinicalImageType, string> = {
  panoramica: 'panorama_wide_angle',
  periapical: 'radio',
  bitewing: 'crop_landscape',
  lateral: 'account_box',
  oclusal: 'crop_square',
  tomografia: 'view_in_ar',
  foto_intraoral: 'photo_camera',
  foto_extraoral: 'face',
  otro: 'image',
};
