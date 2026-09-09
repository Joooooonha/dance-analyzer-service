package SeSAC.Dance_Assessment.Security;

import java.lang.annotation.*;

/**
 * 인증된 사용자 id를 컨트롤러 파라미터로 주입한다.
 *
 * <p>{@code @RequestHeader("X-User-Id")}를 대체한다. 예전에는 클라이언트가 보낸
 * 헤더를 그대로 믿었지만, 이 값은 <b>서명이 검증된 JWT에서만</b> 나온다.
 */
@Target(ElementType.PARAMETER)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface CurrentUserId {
}
