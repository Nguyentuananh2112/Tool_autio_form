// Khớp 1-1 với backend/app/schemas/logic_schema.py và logic_api.py (Soát logic, màn 11)

export type Consistency = 'VARIED' | 'MODERATE' | 'UNIFORM';
export type LogicSource = 'AI' | 'MANUAL' | 'DEMO';
export type ThenOp = 'IS' | 'IS_NOT';
export type RuleStrength = 'ALWAYS' | 'USUALLY';
export type TextSentiment = 'POSITIVE' | 'NEUTRAL' | 'NEGATIVE';

export interface AttitudeItem {
  entry_id: string;
  /** true: đáp án cuối là tích cực nhất; false: đáp án đầu là tích cực nhất */
  positive_high: boolean;
}

export interface AttitudeGroup {
  group_id: string;
  name: string;
  items: AttitudeItem[];
}

export interface LogicRule {
  rule_id: string;
  if_entry: string;
  if_values: string[];
  then_entry: string;
  then_op: ThenOp;
  then_values: string[];
  strength: RuleStrength;
  reason?: string | null;
}

export interface ExclusiveOption {
  entry_id: string;
  value: string;
}

export interface TextAttitude {
  entry_id: string;
  group_id: string;
  labels: Record<string, TextSentiment>;
}

export interface LogicMap {
  version: number;
  attitude_groups: AttitudeGroup[];
  rules: LogicRule[];
  exclusive_options: ExclusiveOption[];
  text_attitudes: TextAttitude[];
  consistency: Consistency;
  source: LogicSource;
  model: string | null;
  analyzed_at: string | null;
  confirmed: boolean;
}

export interface ViolationCount {
  kind: 'RULE' | 'EXCLUSIVE' | 'SPREAD';
  key: string;
  before: number;
  after: number;
}

export interface GroupCorrelation {
  group_id: string;
  name: string;
  before: number | null;
  after: number | null;
}

export interface RatioDrift {
  entry_id: string;
  title: string;
  max_drift_pct: number;
}

export interface SpssAlphaCheck {
  group_id: string;
  name: string;
  target: number | null;
  before: number | null;
  after: number | null;
}

export interface SampleRespondent {
  attitude: string;
  answers: Record<string, string[]>;
}

export interface LogicReviewResult {
  sample_size: number;
  inconsistent_before: number;
  inconsistent_after: number;
  repaired: number;
  regenerated: number;
  violations: ViolationCount[];
  correlations: GroupCorrelation[];
  drifts: RatioDrift[];
  sample: SampleRespondent | null;
  spss_alpha: SpssAlphaCheck[];
  unlabeled_texts: number;
  logic: LogicMap;
  ready: boolean;
}

export type KeySlot = 'USER' | 'SHARED' | 'BACKUP';
export type KeyState = 'MISSING' | 'EXHAUSTED' | 'INVALID' | 'OK';

export interface KeyAttempt {
  slot: KeySlot;
  state: KeyState;
}
