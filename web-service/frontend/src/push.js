/**
 * 브라우저 푸시 구독.
 *
 * 페이지의 `Notification` API로는 **탭이 열려 있을 때만** 알림을 띄울 수 있다.
 * 분석이 3분 넘게 걸려서 그 사이 탭을 닫거나 폰을 잠그는 게 자연스러운데,
 * 그러면 알림을 못 받는다. 서버가 보내는 푸시를 받으려면 서비스 워커를 등록하고
 * 구독 정보를 서버에 올려야 한다.
 *
 * **iOS 주의**: 사파리는 홈 화면에 추가한 경우에만 웹 푸시를 허용한다.
 * 그래서 `isStandalone()`으로 상태를 구분해 안내 문구를 다르게 준다.
 */
import { getPushPublicKey, savePushSubscription, deletePushSubscription } from './api/client';

/** 서버가 주는 base64url 공개키를 pushManager가 받는 바이트 배열로 바꾼다. */
function urlBase64ToUint8Array(base64) {
    const padding = '='.repeat((4 - (base64.length % 4)) % 4);
    const normalized = (base64 + padding).replace(/-/g, '+').replace(/_/g, '/');
    const raw = window.atob(normalized);
    return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

export const pushSupported = () =>
    'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;

/** 홈 화면에 추가된 상태로 실행 중인지. iOS에서 푸시 가능 여부를 가른다. */
export const isStandalone = () =>
    window.matchMedia?.('(display-mode: standalone)').matches ||
    window.navigator.standalone === true;

export const isIOS = () =>
    /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    // 아이패드는 최신 iPadOS에서 맥으로 위장한다
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

let registration = null;

export async function registerServiceWorker() {
    if (!pushSupported()) return null;
    if (registration) return registration;
    try {
        registration = await navigator.serviceWorker.register('/sw.js');
        return registration;
    } catch {
        // 워커 등록에 실패해도 앱은 정상 동작해야 한다. 알림만 못 쓴다.
        return null;
    }
}

/** 이미 구독돼 있는지. UI에서 켜짐/꺼짐을 보여주는 데 쓴다. */
export async function currentSubscription() {
    if (!pushSupported()) return null;
    const reg = await registerServiceWorker();
    if (!reg) return null;
    return reg.pushManager.getSubscription();
}

/**
 * 알림 켜기. 권한 요청은 **사용자 동작 안에서** 불러야 한다 —
 * 브라우저가 그렇지 않은 권한 창을 무시한다.
 *
 * @returns {Promise<'ok'|'denied'|'unsupported'|'no-key'|'error'>}
 */
export async function enablePush() {
    if (!pushSupported()) return 'unsupported';

    const permission = await Notification.requestPermission();
    if (permission !== 'granted') return 'denied';

    const reg = await registerServiceWorker();
    if (!reg) return 'error';

    try {
        const { publicKey } = await getPushPublicKey();
        // 서버에 VAPID 키가 설정되지 않은 환경(개발 등)에서는 구독할 수 없다.
        if (!publicKey) return 'no-key';

        // 이미 구독돼 있으면 그대로 쓴다. 다시 subscribe()를 부르면
        // 브라우저에 따라 기존 구독을 버리고 새로 만들어 서버에 쓰레기가 쌓인다.
        const existing = await reg.pushManager.getSubscription();
        const sub = existing ?? await reg.pushManager.subscribe({
            // 내용 없는 푸시는 대부분의 브라우저가 거부한다. 항상 본문을 보낸다.
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(publicKey),
        });

        await savePushSubscription(sub.toJSON());
        return 'ok';
    } catch {
        return 'error';
    }
}

/** 알림 끄기. 브라우저 구독과 서버 기록을 함께 지운다. */
export async function disablePush() {
    const sub = await currentSubscription();
    if (!sub) return;
    const { endpoint } = sub;
    try {
        await sub.unsubscribe();
    } finally {
        // 브라우저 쪽 해제가 실패해도 서버 기록은 지운다 —
        // 남겨두면 죽은 구독으로 계속 발송을 시도하게 된다.
        try {
            await deletePushSubscription(endpoint);
        } catch { /* 서버가 잠깐 안 될 수도 있다. 다음 구독 때 정리된다. */ }
    }
}
