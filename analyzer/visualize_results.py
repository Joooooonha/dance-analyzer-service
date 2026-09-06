import os
import json
import cv2
import numpy as np
import matplotlib.pyplot as plt

# 1. 프로젝트 루트 경로 설정
proj_root    = os.getcwd()
analysis_dir = os.path.join(proj_root, "analysis_result")

# 2. 최신 결과 JSON 찾기
json_files = [f for f in os.listdir(analysis_dir) if f.endswith(".json")]
latest_json = sorted(json_files)[-1]
result_path = os.path.join(analysis_dir, latest_json)

# 3. JSON 로드
with open(result_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 4. 영상 파일 경로
video_user = os.path.join(proj_root, "data", "user_dancer.mp4")
video_std  = os.path.join(proj_root, "data", "pro_dancer.mp4")

# 5. 비디오 캡처 객체 생성
cap_user = cv2.VideoCapture(video_user)
cap_std  = cv2.VideoCapture(video_std)
fps      = cap_user.get(cv2.CAP_PROP_FPS)

# 6. 시각화 결과 저장 폴더
visuals_dir = os.path.join(proj_root, "visuals")
os.makedirs(visuals_dir, exist_ok=True)

# 7. top_k 구간별 시각화
for entry in data["details"]:
    u_frame = entry["user_frame"]
    s_frame = entry["standard_frame"]
    # top_joints가 [(joint_idx, distance), ...] 형태이므로 j[0] 사용
    joints  = [j[0] for j in entry["joints"]]

    # 사용자 영상 프레임 추출
    cap_user.set(cv2.CAP_PROP_POS_FRAMES, u_frame)
    ret_u, frame_u = cap_user.read()
    # 기준 영상 프레임 추출
    cap_std.set(cv2.CAP_PROP_POS_FRAMES, s_frame)
    ret_s, frame_s = cap_std.read()

    if not ret_u or not ret_s:
        continue

    # BGR → RGB
    frame_u_rgb = cv2.cvtColor(frame_u, cv2.COLOR_BGR2RGB)
    frame_s_rgb = cv2.cvtColor(frame_s, cv2.COLOR_BGR2RGB)

    # 8. 캡처 이미지 파일로 저장
    user_img_path = os.path.join(visuals_dir, f"user_{u_frame}.png")
    std_img_path  = os.path.join(visuals_dir, f"std_{s_frame}.png")
    cv2.imwrite(user_img_path, frame_u)      # BGR 원본 저장
    cv2.imwrite(std_img_path, frame_s)

    # 9. 막대 나란히 표시
    fig, axs = plt.subplots(1, 2, figsize=(10, 5))
    t_u = u_frame / fps
    t_s = s_frame / fps

    axs[0].imshow(frame_u_rgb)
    axs[0].set_title(f"User {t_u:.2f}s")
    axs[0].axis('off')

    axs[1].imshow(frame_s_rgb)
    axs[1].set_title(f"Standard {t_s:.2f}s")
    axs[1].axis('off')

    plt.subplots_adjust(bottom=0.15)

    # figure 좌표로 텍스트 추가 (0~1 사이)
    # x=0.01 (왼쪽 끝 근처), y=0.05 (아래쪽 근처) 
    fig.text(
        0.01, 0.05,
        f"Joints with high error: {joints}",
        ha='left', va='center',
        fontsize=12
    )

    plt.show()

# 자원 해제
cap_user.release()
cap_std.release()