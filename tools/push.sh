#!/bin/sh
# git에는 post-push 훅이 없다 (클라이언트 훅은 pre-push가 끝이고, post-receive는 서버 쪽이다).
# 그래서 push를 감싼다: 푸시가 성공하면 초안 미리보기를 되살린다.
#
#   ./tools/push.sh              현재 브랜치 푸시
#   ./tools/push.sh -u origin main
#
# 푸시가 실패하면 재빌드하지 않는다 — 실패한 상태를 초안으로 덮지 않기 위해서다.
set -e

git push "$@"

echo
echo "푸시 완료. 초안을 포함해 다시 빌드한다 (로컬 미리보기용)."
python3 tools/build.py --drafts
