#!/usr/bin/env bash
#
# 배포 산출물을 만든다. 로컬(맥)에서 실행한다.
#
#   ./deploy/build.sh
#
# 결과:
#   deploy/out/app.jar   → EC2의 /opt/dance-api/app.jar
#   deploy/out/dist/     → EC2의 /var/www/odostudio/dist/
#
# EC2에서 직접 빌드하지 않는 이유: Gradle 빌드가 메모리를 꽤 쓴다.
# 작은 인스턴스에서는 빌드 도중 스왑이 돌거나 OOM으로 죽을 수 있고,
# 그동안 서비스도 같이 느려진다.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/deploy/out"

rm -rf "$OUT"
mkdir -p "$OUT"

echo "==> 프론트엔드 빌드"
cd "$ROOT/web-service/frontend"
# **빈 값이 맞다.** 프론트와 API가 같은 도메인이라 /api/... 요청이 같은
# 오리진으로 나가고, 그래야 httpOnly 쿠키가 자연스럽게 실린다.
# 절대 주소를 넣으면 교차 오리진이 되어 CORS와 쿠키 설정이 복잡해진다.
VITE_API_BASE_URL= npm run build
cp -R dist "$OUT/dist"

echo "==> 백엔드 빌드"
cd "$ROOT/web-service/api-server"
./gradlew clean bootJar -q
cp build/libs/*-SNAPSHOT.jar "$OUT/app.jar"

echo
echo "==> 완료"
ls -lh "$OUT/app.jar"
du -sh "$OUT/dist"
cat <<'NEXT'

다음 단계 (~/.ssh/config 의 'odo' 별칭 사용):

  scp deploy/out/app.jar               odo:/tmp/app.jar
  rsync -av --delete deploy/out/dist/  odo:/tmp/dist/

  # EC2에서 (ssh odo)
  sudo mkdir -p /opt/dance-api /var/www/odostudio
  sudo mv /tmp/app.jar /opt/dance-api/app.jar
  sudo rsync -av --delete /tmp/dist/ /var/www/odostudio/dist/
  sudo systemctl restart dance-api
NEXT
