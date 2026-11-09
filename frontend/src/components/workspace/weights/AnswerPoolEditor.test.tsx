import { fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';

import { AnswerPoolEditor } from './AnswerPoolEditor';

function Harness({ initial }: { initial: string[] }) {
  const [value, setValue] = useState(initial);
  return <AnswerPoolEditor label="Câu trả lời mẫu" value={value} onChange={setValue} emptyHint="Chưa có câu nào" />;
}

describe('ô câu trả lời mẫu dạng danh sách', () => {
  it('mỗi câu một dòng đánh số, xoá được từng câu', () => {
    render(<Harness initial={['giao nhanh', 'giá hơi cao', 'không có gì']} />);
    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(3);
    expect(screen.getByText((_, el) => el?.tagName === 'LABEL' && el.textContent === 'Câu trả lời mẫu · 3 câu')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Xoá câu 2' }));
    expect(screen.getAllByRole('listitem').map((li) => li.textContent)).toEqual(['1giao nhanh', '2không có gì']);
  });

  it('thêm câu bằng Enter, bỏ qua câu trống', () => {
    render(<Harness initial={[]} />);
    expect(screen.getByText('Chưa có câu nào')).toBeInTheDocument();
    const input = screen.getByPlaceholderText(/Thêm một câu/);
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(screen.queryAllByRole('listitem')).toHaveLength(0);
    fireEvent.change(input, { target: { value: '  ship chậm ' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(screen.getByText('ship chậm')).toBeInTheDocument();
    expect(input).toHaveValue('');
  });

  it('dán hàng loạt: mỗi dòng một câu, bỏ dòng trống, tắt kiểm tra chính tả', () => {
    render(<Harness initial={['a']} />);
    fireEvent.click(screen.getByRole('button', { name: /Dán \/ sửa hàng loạt/ }));
    const area = screen.getByRole('textbox');
    expect(area).toHaveAttribute('spellcheck', 'false');
    fireEvent.change(area, { target: { value: 'giao nhanh\n\n  đóng gói đẹp  \nok' } });
    fireEvent.click(screen.getByRole('button', { name: /Xem dạng danh sách/ }));
    expect(screen.getAllByRole('listitem').map((li) => li.textContent)).toEqual(['1giao nhanh', '2đóng gói đẹp', '3ok']);
  });
});
