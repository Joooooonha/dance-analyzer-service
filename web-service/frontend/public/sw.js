/**
 * 서비스 워커 — 브라우저를 닫아도 알림이 뜨게 하는 유일한 방법.
 *
 * 페이지의 `Notification` API는 그 탭이 열려 있을 때만 동작한다. 분석이 3분
 * 넘게 걸려서 그 사이 탭을 닫거나 폰을 잠그는 것이 자연스러운데, 그러면
 * 알림을 받을 수 없었다. 서버가 푸시를 보내면 브라우저가 이 워커를 깨워
 * 알림을 띄운다 — 페이지가 없어도 된다.
 *
 * iOS는 **홈 화면에 추가한 경우에만** 웹 푸시를 허용한다. 그래서 manifest도 같이 둔다.
 */

self.addEventListener('install', () => {
    // 새 워커가 바로 일하게 한다. 안 그러면 기존 탭이 모두 닫힐 때까지
    // 예전 워커가 남아서, 고친 알림 동작이 언제 반영될지 알 수 없다.
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(self.clients.claim());
});

self.addEventListener('push', (event) => {
    // 본문이 없거나 JSON이 아닐 수 있다(브라우저 점검용 빈 푸시 등).
    // 그때도 알림은 떠야 한다 — 조용히 사라지면 사용자는 알림이 고장 났다고 여긴다.
    let data = {};
    try {
        data = event.data ? event.data.json() : {};
    } catch {
        data = { body: event.data ? event.data.text() : '' };
    }

    const title = data.title || 'Dance Analyzer';
    event.waitUntil(
        self.registration.showNotification(title, {
            body: data.body || '',
            icon: '/icon-192.png',
            badge: '/icon-192.png',
            // 같은 기록의 알림이 여러 번 오면 쌓이지 않고 최신 것으로 대체된다.
            tag: data.url || 'dance-analyzer',
            renotify: true,
            data: { url: data.url || '/' },
        })
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const target = (event.notification.data && event.notification.data.url) || '/';

    // 이미 열려 있는 창이 있으면 새 창을 띄우지 않고 그쪽을 쓴다.
    // 알림을 누를 때마다 탭이 하나씩 늘어나면 성가시다.
    event.waitUntil(
        self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
            for (const client of list) {
                if ('focus' in client) {
                    client.navigate(target);
                    return client.focus();
                }
            }
            return self.clients.openWindow(target);
        })
    );
});
