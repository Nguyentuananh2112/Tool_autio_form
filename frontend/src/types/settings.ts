// Khớp backend/app/schemas/misc_api.py + cầu nối với vỏ app desktop (Phase 5)

export interface AppSettingsRead {
  app_version: string;
  data_dir: string;
  gemini_model: string;
  gemini_key_configured: boolean;
}

export interface GeneratePoolRequest {
  question_title: string;
  survey_context: string;
  count: number;
  persona?: string;
}

export interface BrowserStatus {
  installed: boolean;
  installing: boolean;
  percent: number | null;
  detail: string | null;
  error: string | null;
}

export interface ApiErrorBody {
  message: string;
  errors: string[];
}

export interface UpdateInfo {
  version: string;
  releaseDate: string;
  notes: string[];
  sizeBytes: number;
}

/** Vỏ desktop gắn `window.autoformDesktop`; chạy trong trình duyệt thường thì không có. */
export interface DesktopBridge {
  version: string;
  openPath?: (path: string) => Promise<void>;
  updater?: {
    check: () => Promise<UpdateInfo | null>;
    download: (onProgress: (percent: number) => void) => Promise<void>;
    installAndRestart: () => Promise<void>;
    installOnQuit: () => Promise<void>;
  };
}

export interface RuntimeConfig {
  apiBase: string;
  wsBase: string;
  token: string | null;
}

declare global {
  interface Window {
    autoformDesktop?: DesktopBridge;
    __AUTOFORM_CONFIG__?: Partial<RuntimeConfig>;
  }
}
