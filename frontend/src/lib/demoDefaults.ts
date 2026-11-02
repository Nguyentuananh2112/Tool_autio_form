import type { CampaignCreate, QuestionRuleConfig } from '@/types/campaign';

export const PRACTICE_CAMPAIGN_NAME = 'Chiến dịch tập dùng (mô phỏng)';

/** Luật tối thiểu để form mẫu chạy được (câu tự luận bắt buộc cần câu trả lời mẫu). */
export const DEMO_RULES: QuestionRuleConfig[] = [
  { entry_id: '1004', question_type: 4, weights: { 'Quán gần nhà': 60, 'Chuỗi cà phê': 50, 'Tự pha ở nhà': 30, 'Ứng dụng giao hàng': 25 }, max_checked: 2 },
  { entry_id: '1040', question_type: 0, text_pool: ['Thêm chỗ ngồi yên tĩnh', 'Giảm giá cho sinh viên', 'Wifi mạnh hơn', 'Mở cửa sớm hơn', 'Nhiều lựa chọn ít đường'] },
];

export function practiceCampaign(formId: string): CampaignCreate {
  return {
    form_id: formId,
    name: PRACTICE_CAMPAIGN_NAME,
    data_source: 'PROBABILITY',
    total_target: 40,
    schedule: { mode: 'SCHEDULED', duration_minutes: 2, concurrency: 1 },
    rules: DEMO_RULES,
    spss_groups: [],
    excel_records: null,
    proxy: null,
    use_playwright_fallback: false,
  };
}
