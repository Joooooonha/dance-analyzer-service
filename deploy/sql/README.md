# 이 폴더는 이제 기록용입니다

여기 있는 SQL은 **Flyway를 도입하기 전에** 손으로 돌렸던 마이그레이션입니다.
운영 DB에는 이미 전부 적용돼 있고, 그 결과가
`web-service/api-server/src/main/resources/db/migration/V1__baseline_schema.sql`
에 하나로 합쳐져 있습니다.

**앞으로 스키마를 바꿀 때는 여기에 파일을 만들지 마세요.** 대신:

```
web-service/api-server/src/main/resources/db/migration/V2__무엇을_바꾸는지.sql
```

앱이 기동할 때 Flyway가 알아서 적용합니다. 사람이 순서를 지킬 필요가 없고,
적용 이력이 `flyway_schema_history` 테이블에 남습니다.

## 규칙 두 가지

1. **이미 적용된 파일은 고치지 않는다.** Flyway가 체크섬을 비교해서, 내용이
   바뀌면 기동을 거부합니다. 잘못 만들었으면 되돌리는 마이그레이션을 새로 씁니다.
2. **되돌리는 SQL을 주석으로 같이 적어둔다.** 자동 롤백은 없습니다.

## 왜 손으로 돌리던 방식을 버렸나

운영이 `ddl-auto=validate`라 스키마 변경 SQL을 **새 jar보다 먼저** 돌려야 했고,
순서를 틀리면 애플리케이션이 아예 뜨지 않았습니다. 사람이 매번 순서를 기억해야
하는 구조는 배포를 자동화할 수 없습니다.
