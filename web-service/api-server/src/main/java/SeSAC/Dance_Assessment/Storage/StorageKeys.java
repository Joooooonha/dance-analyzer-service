package SeSAC.Dance_Assessment.Storage;

import java.util.UUID;

/**
 * 저장소 객체 키 규칙.
 *
 * <p>키에 사용자가 올린 파일명을 그대로 쓰지 않는다. 한글·공백·경로 문자(`../`)가
 * 섞여 들어오면 키가 깨지거나 다른 경로를 가리킬 수 있고, 파일명 자체가 개인정보가
 * 되기도 한다. 확장자만 남기고 UUID로 새로 짓는다.
 */
public final class StorageKeys {

    private StorageKeys() {
    }

    public static String video(Long uploaderId, String originalFilename) {
        return "videos/%d/%s%s".formatted(uploaderId, UUID.randomUUID(), extensionOf(originalFilename));
    }

    /** 분석 결과 비교 이미지. {@code slot}은 지적 구간 순위(0부터). */
    public static String issueImage(Long logId, String runId, int slot) {
        return "results/%d/%s/issue_%02d.jpg".formatted(logId, runId, slot);
    }

    public static String comparisonVideo(Long logId, String runId) {
        return "results/%d/%s/comparison.mp4".formatted(logId, runId);
    }

    /**
     * 확장자만 뽑는다. 없거나 수상하면 빈 문자열.
     * 점 뒤가 너무 길거나 영숫자가 아니면 확장자로 보지 않는다.
     */
    static String extensionOf(String filename) {
        if (filename == null) {
            return "";
        }
        int dot = filename.lastIndexOf('.');
        if (dot < 0 || dot == filename.length() - 1) {
            return "";
        }
        String ext = filename.substring(dot + 1);
        if (ext.length() > 5 || !ext.chars().allMatch(Character::isLetterOrDigit)) {
            return "";
        }
        return "." + ext.toLowerCase();
    }
}
