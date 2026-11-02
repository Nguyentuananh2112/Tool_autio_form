/** 5 dòng đầu của file như người dùng đã nhập. */
export function ExcelPreviewTable({ columns, rows }: { columns: string[]; rows: Record<string, unknown>[] }) {
  const shown = columns.slice(0, 8);
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] border-collapse text-[13px]">
        <thead>
          <tr className="text-left text-xs text-muted">
            <th scope="col" className="px-5 py-2.5 font-semibold">Dòng</th>
            {shown.map((c) => <th key={c} scope="col" className="px-3 py-2.5 font-semibold">{c}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t border-line">
              <td className="px-5 py-2.5 font-mono">{i + 2}</td>
              {shown.map((c) => <td key={c} className="px-3 py-2.5">{row[c] === null || row[c] === undefined ? '—' : String(row[c])}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
      {columns.length > shown.length && <p className="m-0 px-5 py-2 text-xs text-muted">Đang hiện {shown.length} / {columns.length} cột.</p>}
    </div>
  );
}
