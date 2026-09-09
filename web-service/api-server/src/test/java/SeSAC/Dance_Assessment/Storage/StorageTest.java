package SeSAC.Dance_Assessment.Storage;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import java.net.URI;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * 저장소 접근 통제 검증.
 *
 * <p>저장소는 <b>서명된 URL로만</b> 열린다. 서명이 없거나 틀리거나 만료됐으면
 * 열리지 않아야 한다 — 이게 뚫리면 버킷을 공개해둔 것과 같아지고, Spring이 하는
 * 권한 검사가 통째로 무의미해진다.
 */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("dev")
class StorageTest {

    @Autowired
    MockMvc mvc;

    @Autowired
    LocalStorageService storage;

    /** 서명 URL에서 쿼리 파라미터를 뽑는다. */
    private Map<String, String> paramsOf(String url) {
        String query = URI.create(url).getQuery();
        return java.util.Arrays.stream(query.split("&"))
                .map(kv -> kv.split("=", 2))
                .collect(java.util.stream.Collectors.toMap(
                        a -> a[0],
                        a -> java.net.URLDecoder.decode(a[1], java.nio.charset.StandardCharsets.UTF_8)));
    }

    @Test
    @DisplayName("올린 파일을 서명 URL로 다시 받을 수 있다")
    void uploadThenDownload() throws Exception {
        String key = "videos/1/roundtrip-test.mp4";
        byte[] body = "hello-video".getBytes();

        var up = paramsOf(storage.createUploadUrl(key, "video/mp4"));
        mvc.perform(put("/api/local-storage")
                        .param("key", key)
                        .param("method", "PUT")
                        .param("exp", up.get("exp"))
                        .param("sig", up.get("sig"))
                        .content(body))
                .andExpect(status().isOk());

        var down = paramsOf(storage.createDownloadUrl(key));
        byte[] got = mvc.perform(get("/api/local-storage")
                        .param("key", key)
                        .param("method", "GET")
                        .param("exp", down.get("exp"))
                        .param("sig", down.get("sig")))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsByteArray();

        assertThat(got).isEqualTo(body);
    }

    @Test
    @DisplayName("[핵심] 서명이 없거나 틀리면 거부된다")
    void unsignedAccessIsRejected() throws Exception {
        String key = "videos/1/roundtrip-test.mp4";

        mvc.perform(get("/api/local-storage").param("key", key)
                        .param("method", "GET").param("exp", "99999999999").param("sig", "fake"))
                .andExpect(status().isForbidden());

        // 다른 키의 서명을 가져다 쓰는 것도 막혀야 한다
        var other = paramsOf(storage.createDownloadUrl("videos/1/other.mp4"));
        mvc.perform(get("/api/local-storage").param("key", key)
                        .param("method", "GET")
                        .param("exp", other.get("exp"))
                        .param("sig", other.get("sig")))
                .andExpect(status().isForbidden());
    }

    @Test
    @DisplayName("만료된 URL은 거부된다")
    void expiredUrlIsRejected() {
        String key = "videos/1/expired.mp4";
        long past = java.time.Instant.now().minusSeconds(60).getEpochSecond();

        assertThatThrownBy(() -> storage.verifyAndResolve(
                key, "GET", past, storage.sign(key, "GET", past)))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("만료");
    }

    @Test
    @DisplayName("다운로드 서명으로 업로드할 수 없다")
    void downloadSignatureCannotUpload() throws Exception {
        String key = "videos/1/method-swap.mp4";
        var down = paramsOf(storage.createDownloadUrl(key));

        // method가 서명에 포함되므로 GET 서명으로 PUT을 시도하면 서명이 안 맞는다
        mvc.perform(put("/api/local-storage").param("key", key)
                        .param("method", "PUT")
                        .param("exp", down.get("exp"))
                        .param("sig", down.get("sig"))
                        .content("evil"))
                .andExpect(status().isForbidden());
    }

    @Test
    @DisplayName("[핵심] 상위 경로(../)로 저장 폴더를 벗어날 수 없다")
    void pathTraversalIsBlocked() {
        long exp = java.time.Instant.now().plusSeconds(600).getEpochSecond();
        String evil = "../../../etc/passwd";

        // 서명은 올바르게 만들어 줘도(=키를 만드는 쪽이 뚫린 상황을 가정) 경로
        // 검사에서 막혀야 한다.
        assertThatThrownBy(() -> storage.verifyAndResolve(
                evil, "GET", exp, storage.sign(evil, "GET", exp)))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("잘못된 키");
    }

    @Test
    @DisplayName("객체 키에 원본 파일명을 그대로 쓰지 않는다")
    void keysDoNotEmbedUserFilenames() {
        String key = StorageKeys.video(7L, "내 영상 (최종)(진짜최종).MOV");

        assertThat(key).startsWith("videos/7/");
        assertThat(key).endsWith(".mov");          // 확장자만 살린다
        assertThat(key).doesNotContain(" ");       // 공백/한글이 키에 들어가면 안 된다
        assertThat(key).doesNotContain("최종");

        // 경로 문자가 섞인 파일명도 확장자로 오인되면 안 된다
        assertThat(StorageKeys.extensionOf("../../etc/passwd")).isEmpty();
        assertThat(StorageKeys.extensionOf("noext")).isEmpty();
        assertThat(StorageKeys.extensionOf("a.mp4")).isEqualTo(".mp4");
    }
}
