// Khớp 1-1 với backend/app/schemas/form_schema.py và form_api.py

export const OTHER_OPTION_VALUE = '__other_option__';

export type NavigationAction = 'NEXT_PAGE' | 'SUBMIT' | 'GO_TO_PAGE';

export interface ParsedOption {
  label: string;
  value: string;
  is_other: boolean;
  jump_to_section_id: number | null;
}

export interface ParsedSection {
  page_index: number;
  section_item_id: number | null;
  title: string;
  description: string | null;
  navigation_action: NavigationAction;
  jump_to_section_id: number | null;
}

export interface ParsedQuestion {
  item_id: number;
  entry_id: string;
  title: string;
  description: string | null;
  type_id: number;
  type_name: string;
  page_index: number;
  is_required: boolean;
  options: ParsedOption[];
  scale_low_label: string | null;
  scale_high_label: string | null;
  grid_item_id: number | null;
  grid_title: string | null;
  row_label: string | null;
  is_multi_select: boolean;
}

export interface ParsedFormStructure {
  title: string;
  description: string | null;
  view_url: string;
  submit_url: string;
  fbzx: string | null;
  total_pages: number;
  sections: ParsedSection[];
  questions: ParsedQuestion[];
}

export interface FormSummary {
  id: string;
  title: string;
  view_url: string;
  submit_url: string;
  total_pages: number;
  question_count: number;
  is_demo: boolean;
  created_at: string;
}

export interface FormDetail extends FormSummary {
  structure: ParsedFormStructure;
}

export const QuestionType = {
  SHORT_ANSWER: 0,
  PARAGRAPH: 1,
  MULTIPLE_CHOICE: 2,
  DROPDOWN: 3,
  CHECKBOX: 4,
  LINEAR_SCALE: 5,
  GRID: 7,
  DATE: 9,
  TIME: 10,
} as const;
