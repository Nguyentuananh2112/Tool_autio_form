import { computePopoverPosition, POPOVER_WIDTH } from '@/components/tour/popoverPosition';
import { sampleStructure } from '@/test/fixtures';

import { estimateBranchPaths } from './branchPaths';
import { presetWeights } from './presets';
import { detectMaxChecked, isBranching, questionCode, scaleValues } from './questions';
import { computeReadiness } from './readiness';

describe('presetWeights', () => {
  it.each(['uniform', 'bell', 'agree'] as const)('%s luôn cộng đủ 100', (kind) => {
    for (const count of [2, 3, 5, 7, 10]) expect(presetWeights(kind, count).reduce((a, b) => a + b, 0)).toBe(100);
  });
  it('hình chuông cao nhất ở giữa, nghiêng về cao tăng dần', () => {
    const bell = presetWeights('bell', 5);
    expect(Math.max(...bell)).toBe(bell[2]);
    const agree = presetWeights('agree', 5);
    expect([...agree].sort((a, b) => a - b)).toEqual(agree);
  });
});

describe('questions', () => {
  const s = sampleStructure();
  it('nhận mã câu, "tối đa N" và câu rẽ nhánh', () => {
    expect(questionCode(s.questions[1]!)).toBe('A3');
    expect(detectMaxChecked(s.questions[2]!)).toBe(2);
    expect(isBranching(s.questions[1]!)).toBe(true);
    expect(isBranching(s.questions[0]!)).toBe(false);
  });
  it('thang số liên tiếp dùng giá trị thật, còn lại dùng 1..K', () => {
    const scale = { ...s.questions[0]!, options: ['1', '2', '3'].map((v) => ({ label: v, value: v, is_other: false, jump_to_section_id: null })) };
    expect(scaleValues(scale)).toEqual([1, 2, 3]);
    expect(scaleValues(s.questions[0]!)).toEqual([1, 2]);
  });
});

describe('estimateBranchPaths', () => {
  it('khớp luật rẽ nhánh của backend (B nhảy tới D)', () => {
    const paths = estimateBranchPaths(sampleStructure(), { '2': { entry_id: '2', question_type: 2, weights: { 'Có': 70, 'Không': 30 } } });
    expect(paths.map((p) => p.pages.join(','))).toEqual(['0,1,3', '0,2,3']);
    expect(paths[0]!.probability).toBeCloseTo(0.7);
  });
});

describe('computeReadiness', () => {
  it('báo câu tự luận bắt buộc thiếu mẫu và "Mục khác" thiếu nội dung', () => {
    const s = sampleStructure();
    const ready = computeReadiness(s, { '1': { entry_id: '1', question_type: 2, weights: { Nam: 50, '__other_option__': 50 } } }, []);
    expect(ready.issues.map((i) => i.entryId).sort()).toEqual(['1', '5']);
    expect(ready.missingTextCount).toBe(1);
    const fixed = computeReadiness(s, { '5': { entry_id: '5', question_type: 0, text_pool: ['Ổn'] } }, []);
    expect(fixed.issues).toHaveLength(0);
  });
});

describe('computePopoverPosition', () => {
  const rect = (left: number, top: number, w = 200, h = 80) => new DOMRect(left, top, w, h);
  it('đổi hướng khi không đủ chỗ và luôn nằm trong màn hình', () => {
    const right = computePopoverPosition(rect(1200, 100), 'right', 1440, 900);
    expect(right.placement).not.toBe('right');
    const below = computePopoverPosition(rect(1350, 100), 'below', 1440, 900);
    expect(below.left + POPOVER_WIDTH).toBeLessThanOrEqual(1440 - 16);
  });
});
