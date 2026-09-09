-- 나란히 비교(동작 대응표)와 분석 진행 표시를 위한 컬럼 추가.
--
-- 운영은 spring.jpa.hibernate.ddl-auto=validate라 컬럼이 자동으로 생기지 않는다.
-- **이 스크립트를 먼저 돌린 뒤에** 새 jar를 올릴 것. 순서를 바꾸면 Hibernate가
-- 스키마 검증에 실패해 애플리케이션이 아예 뜨지 않는다.
--
--   ssh odo 'sudo -u postgres psql -d dance_db' < deploy/sql/002-sync-map.sql
--
-- 되돌리기:
--   ALTER TABLE analysis_result DROP COLUMN sync_map_json, DROP COLUMN analysis_job_id;

-- 두 영상을 맞춰 재생하기 위한 대응표 [[연습 시각, 기준 시각], ...] (초).
--
-- **text다. 기존 @Lob 컬럼들처럼 oid가 아니다.** Hibernate 6에서 @Lob String은
-- PostgreSQL의 Large Object(oid)로 매핑되는데, 그러면 값이 테이블 밖에 저장돼
-- psql로 그냥 조회하면 숫자 하나만 나온다(convert_from(lo_get(...))로 읽어야 한다).
-- 엔티티에서 @JdbcTypeCode(SqlTypes.LONGVARCHAR)를 써서 text로 맞췄다.
ALTER TABLE analysis_result ADD COLUMN IF NOT EXISTS sync_map_json text;

-- 이번 분석 실행의 표식. 진행 상황을 물어볼 때 "내 작업이 맞는지" 대조한다.
-- 분석 서버는 진행 상황을 한 건분만 들고 있어서, 대조하지 않으면 다른 사용자의
-- 진행률을 보여주게 된다.
ALTER TABLE analysis_result ADD COLUMN IF NOT EXISTS analysis_job_id varchar(255);
