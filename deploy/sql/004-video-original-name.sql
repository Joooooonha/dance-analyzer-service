-- 영상의 원래 파일 이름.
--
-- 기준 영상을 다시 쓰려면 목록에서 골라야 하는데, 저장소 키는
-- `videos/{사용자}/{임의값}.{확장자}` 형태라 사람이 알아볼 단서가 없다.
-- "9월 9일 15:32에 올린 영상"만으로는 어느 안무인지 알 수 없다.
--
-- 기존 행에는 값이 없다(NULL). 화면이 업로드 시각으로 대체 표시한다.
--
-- 운영은 ddl-auto=validate라 **새 jar보다 먼저** 돌릴 것.
--   ssh odo 'sudo -u postgres psql -d dance_db' < deploy/sql/004-video-original-name.sql
--
-- 되돌리기: ALTER TABLE video DROP COLUMN original_name;

ALTER TABLE video ADD COLUMN IF NOT EXISTS original_name varchar(255);
