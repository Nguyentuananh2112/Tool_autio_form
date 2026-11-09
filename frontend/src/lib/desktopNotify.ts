/**
 * Thông báo hệ thống (Windows) khi app không ở trước mặt người dùng (màn 13).
 * Dùng Notification của trình duyệt — trong Electron nó hiện thành thông báo Windows thật.
 */
export function shouldNotifyDesktop(): boolean {
  return typeof document !== 'undefined' && (document.hidden || !document.hasFocus());
}

export function notifyDesktop(title: string, body: string, onClick: () => void): void {
  if (typeof Notification === 'undefined' || !shouldNotifyDesktop()) return;
  const show = () => {
    const notification = new Notification(title, { body, tag: title });
    notification.onclick = () => {
      void window.autoformDesktop?.focusWindow?.();
      window.focus();
      onClick();
      notification.close();
    };
  };
  if (Notification.permission === 'granted') show();
  else if (Notification.permission !== 'denied') void Notification.requestPermission().then((p) => p === 'granted' && show());
}
