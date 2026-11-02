import { useEffect, useState } from 'react';

import { useThemeStore } from '@/store/themeStore';

export interface ChartColors {
  series1: string;
  series2: string;
  grid: string;
  muted: string;
  ink: string;
  surface: string;
}

const read = (): ChartColors => {
  const css = getComputedStyle(document.documentElement);
  const v = (name: string, fallback: string) => css.getPropertyValue(name).trim() || fallback;
  return {
    series1: v('--series-1', '#2563eb'),
    series2: v('--series-2', '#0e9384'),
    grid: v('--grid', '#e2e5ea'),
    muted: v('--muted', '#4b5563'),
    ink: v('--ink', '#111827'),
    surface: v('--surface', '#ffffff'),
  };
};

/** SVG của Recharts không đọc được biến CSS trong thuộc tính → đọc giá trị thật, cập nhật khi đổi theme. */
export function useChartColors(): ChartColors {
  const preference = useThemeStore((s) => s.preference);
  const [colors, setColors] = useState<ChartColors>(read);
  useEffect(() => {
    // Đợi class "dark" được gắn xong rồi mới đọc
    const id = requestAnimationFrame(() => setColors(read()));
    return () => cancelAnimationFrame(id);
  }, [preference]);
  useEffect(() => {
    if (preference !== 'system' || !window.matchMedia) return undefined;
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => requestAnimationFrame(() => setColors(read()));
    media.addEventListener('change', onChange);
    return () => media.removeEventListener('change', onChange);
  }, [preference]);
  return colors;
}
