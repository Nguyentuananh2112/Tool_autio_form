/** Preset tỷ lệ cho câu một lựa chọn (Mục 7 spec): kết quả là % nguyên, tổng = 100. */
export type PresetKind = 'uniform' | 'bell' | 'agree';

export const PRESET_LABELS: Record<PresetKind, string> = {
  uniform: 'Phân phối đều',
  bell: 'Hình chuông',
  agree: 'Nghiêng về cao',
};

function normalizeTo100(raw: number[]): number[] {
  const total = raw.reduce((sum, v) => sum + v, 0);
  if (total <= 0 || raw.length === 0) return raw.map(() => 0);
  const scaled = raw.map((v) => (v * 100) / total);
  const floored = scaled.map(Math.floor);
  let remainder = 100 - floored.reduce((sum, v) => sum + v, 0);
  // Phần dư chia cho các ô có phần thập phân lớn nhất
  const order = scaled.map((v, i) => ({ i, frac: v - Math.floor(v) })).sort((a, b) => b.frac - a.frac);
  for (const { i } of order) {
    if (remainder <= 0) break;
    floored[i] = (floored[i] ?? 0) + 1;
    remainder -= 1;
  }
  return floored;
}

export function presetWeights(kind: PresetKind, count: number): number[] {
  if (count <= 0) return [];
  const indices = Array.from({ length: count }, (_, i) => i);
  if (kind === 'uniform') return normalizeTo100(indices.map(() => 1));
  if (kind === 'bell') {
    const center = (count - 1) / 2;
    const spread = Math.max(count / 4, 0.75);
    return normalizeTo100(indices.map((i) => Math.exp(-((i - center) ** 2) / (2 * spread ** 2))));
  }
  // Nghiêng về các mức cao (VD Đồng ý / Rất đồng ý)
  return normalizeTo100(indices.map((i) => (i + 1) ** 2));
}
