# Thiết kế UI/UX — Auto-Form (desktop)

**Trạng thái:** ĐÃ DUYỆT (2026-11-02). Frontend (Phase 4) phải bám sát bản này; thay đổi giao diện đáng kể cần thiết kế lại và xin duyệt trước khi code.

**Bản thiết kế (canvas):** https://claude.ai/artifact/HBfvuS7c5uqH4ChJzsnKjm — riêng tư, chỉ chủ sở hữu mở được cho tới khi chia sẻ.

## Các màn hình
| # | Artboard | Màn hình | File React dự kiến |
|---|---|---|---|
| 1 | `Main.dc.html` | Tổng quan: KPI, chiến dịch gần đây, phân tích nhanh, banner cập nhật | `pages/DashboardPage.tsx` |
| 2 | `Workspace.dc.html` | Cấu hình khảo sát: danh sách trang, thẻ câu hỏi theo loại, thiết lập chạy | `pages/FormWorkspacePage.tsx` |
| 3 | `SpssGroup.dc.html` | Hộp thoại nhóm SPSS: chọn biến, mean/SD/r, preview Cronbach's Alpha | `components/spss/SpssGroupDialog.tsx` |
| 4 | `Campaign.dc.html` | Giám sát chiến dịch: KPI, tiến độ, phân phối, nhịp gửi, nhật ký trực tiếp | `pages/CampaignDetailPage.tsx` |
| 5 | `Update.dc.html` | Luồng cập nhật: có bản mới → tải → sẵn sàng → khởi động lại (bấm thử được) | `components/update/*` |
| 6 | `Settings.dc.html` | Cài đặt: Gemini key, cập nhật & kênh, giao diện, mặc định, dữ liệu | `pages/SettingsPage.tsx` |
| 7 | `DesignSystem.dc.html` | Token màu sáng/tối, chữ, nút, badge, ô nhập | `styles/tokens.css`, `components/ui/*` |
| — | `Sidebar.dc.html` | Thanh điều hướng dùng chung | `components/layout/Sidebar.tsx` |

## Quyết định thiết kế
- **Không có màn hình đăng nhập** (người dùng xác nhận — SPEC-011): app desktop, mỗi máy một người dùng.
- **Nhãn thân thiện thay thuật ngữ kỹ thuật**: "Tốc độ tối đa" (BURST), "Rải đều tự nhiên" (SCHEDULED), "Dùng trình duyệt khi bị chặn" (Playwright fallback), "Gửi trực tiếp" (HTTPX).
- **Chặn chạy khi cấu hình chưa đủ**: nút "Bắt đầu chạy" bị khóa kèm lý do (VD: 7 câu tự luận thiếu mẫu) — tránh lỗi `GeneratorConfigError` lúc chạy.
- **Hiển thị đường đi rẽ nhánh** dự kiến (Workspace) và thực tế (Campaign) — rút ra từ lỗi CONF-001.
- **Cập nhật không làm hỏng chiến dịch đang chạy**: tự tạm dừng an toàn trước khi cài, tự chạy tiếp sau khi mở lại. Người dùng chọn "Để sau" / "Cài khi tắt ứng dụng".
- **Chromium chỉ tải khi bật tính năng trình duyệt dự phòng** (RISK-006).
- Font: Be Vietnam Pro (giao diện), JetBrains Mono (mã, nhật ký). Màu nhấn xanh dương; cảnh báo cam, thành công xanh lá, lỗi đỏ — phân biệt cả bằng độ sáng.

## Chia nhỏ component (chống God Component)
```text
frontend/src/
├── components/
│   ├── ui/                 # Button, Badge, Card, Input, Switch, Slider, Alert, ProgressBar, Dialog
│   ├── layout/             # AppShell, Sidebar, PageHeader
│   ├── dashboard/          # KpiCard, KpiGrid, CampaignTable, CampaignRow, QuickParseCard, RecentForms
│   ├── workspace/
│   │   ├── FormUrlBar.tsx, SourceTabs.tsx, MissingConfigAlert.tsx, PageRail.tsx
│   │   ├── question-cards/ # QuestionCard (khung chung) + ChoiceCard, BranchingCard, CheckboxCard,
│   │   │                   #   TextPoolCard, GridRowCard, ScaleCard, DateTimeCard
│   │   ├── weights/        # WeightSliderRow, PresetButtons, WeightTotal, BranchPathPreview
│   │   └── run-settings/   # TargetInput, ModePicker, ProxyField, FallbackSwitch, ReadinessChecklist, StartButton
│   ├── spss/               # SpssGroupDialog, ItemPicker, TargetParams, AlphaResult, ItemDistribution
│   ├── campaign/           # CampaignHeader, KpiStrip, LiveProgress, DistributionChart, PaceChart, PathStats, LiveLog
│   ├── update/             # UpdateBanner, UpdateDialog, DownloadProgress, ReadyToInstall, UpdateToast
│   └── settings/           # GeminiKeySection, UpdateSection, AppearanceSection, DefaultsSection, DataSection
├── hooks/                  # useCampaignSocket, useUpdater, useFormParse, useSpssPreview
├── store/                  # Zustand: formConfigStore, campaignStore, settingsStore, updateStore
└── pages/                  # Chỉ ghép component, không chứa logic nghiệp vụ
```
Quy tắc: page chỉ ghép component; logic gọi API/WebSocket nằm trong `hooks/`; mỗi loại câu hỏi một card riêng dùng chung khung `QuestionCard`.
