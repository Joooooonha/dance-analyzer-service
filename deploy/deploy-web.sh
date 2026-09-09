#!/usr/bin/env bash
#
# 프론트엔드만 다시 배포한다. 로컬(맥)에서 실행.
#
#   ./deploy/deploy-web.sh
#
# API(jar)는 건드리지 않으므로 서비스 재시작도, 다운타임도 없다.
# nginx가 정적 파일을 그대로 서빙할 뿐이다.
# 백엔드까지 바뀌었다면 ./deploy/build.sh 쪽을 쓸 것.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${WEB_HOST:-odo}"
DEST="${WEB_DEST:-/var/www/odostudio/dist}"

cd "$ROOT/web-service/frontend"

echo "==> 빌드"
# **VITE_API_BASE_URL을 빈 값으로 넘기는 것이 핵심이다.**
# 그냥 `npm run build`를 하면 client.js의 기본값(http://localhost:8080)이
# 번들에 박혀서, 배포된 화면이 사용자의 로컬 8080으로 API를 호출한다.
# 전부 실패하는데 화면은 멀쩡해 보여서 원인을 찾기 어렵다.
# 빈 값이면 `/api/...`가 같은 오리진으로 나가고 httpOnly 쿠키도 자연스럽게 실린다.
VITE_API_BASE_URL= npm run build

echo
echo "==> 확인: 번들에 localhost가 박히지 않았는지"
if grep -rq "localhost:8080" dist/assets/*.js; then
  echo "❌ 번들에 localhost:8080이 들어 있습니다. 빌드 환경변수를 확인하세요."
  exit 1
fi
echo "   OK"

echo
echo "==> 업로드: $HOST:$DEST"
# --delete로 예전 해시의 asset을 정리한다. 놔두면 배포할 때마다 쌓인다.
rsync -a --delete dist/ "$HOST:/tmp/dist-web/"
ssh "$HOST" "sudo rsync -a --delete /tmp/dist-web/ $DEST/ && rm -rf /tmp/dist-web"

echo
echo "==> 확인"
BUNDLE=$(ssh "$HOST" "ls $DEST/assets/index-*.js | xargs -n1 basename")
SERVED=$(curl -s https://odostudio.site/ | grep -o 'assets/index-[A-Za-z0-9_-]*\.js' | head -1)
echo "   서버 파일 : $BUNDLE"
echo "   서빙 중   : ${SERVED#assets/}"
if [ "$BUNDLE" = "${SERVED#assets/}" ]; then
  echo "   ✅ 반영됨"
else
  echo "   ⚠️ 다릅니다 — Cloudflare가 index.html을 캐시하고 있을 수 있습니다."
  echo "      Caching → Configuration → Purge Cache 에서 https://odostudio.site/ 를 비우세요."
fi
