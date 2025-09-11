import os
import glob
from typing import Optional

# environment.py 파일에서 직접 만든 로봇 팔 환경을 가져옵니다.
from environment import RoboticArmEnv
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback

# --- 1. 상수 및 경로 설정 ---
TENSORBOARD_LOG_DIR = "tensorboard_logs/" # 텐서보드 로그 저장 경로
CHECKPOINT_DIR = "checkpoints/" # 모델 중간 저장 경로
FINAL_MODEL_PATH = "final_model.zip" # 최종 모델 저장 이름

TOTAL_TIMESTEPS = 1_000_000 # 총 훈련 횟수
CHECKPOINT_FREQ = 10_000 # 중간 저장 빈도
CHECKPOINT_PREFIX = "ppo_robotic_arm" # 중간 저장 파일 이름

def find_latest_checkpoint(directory: str, prefix: str) -> Optional[str]:
    """
    지정된 경로에서 가장 최근에 저장된 모델 파일을 찾습니다.
    """
    # 'checkpoints/ppo_robotic_arm_*_steps.zip' 패턴의 모든 파일을 찾습니다.
    checkpoint_files = glob.glob(os.path.join(directory, f"{prefix}_*_steps.zip"))
    
    if not checkpoint_files:
        print("저장된 체크포인트가 없습니다.")
        return None
        
    # 파일 이름에서 숫자 부분을 추출하여 가장 큰 값을 가진 파일을 찾습니다.
    try:
        latest_checkpoint = max(
            checkpoint_files, 
            key=lambda x: int(os.path.basename(x).split('_')[-2])
        )
        return latest_checkpoint
    except (ValueError, IndexError):
        print("체크포인트 파일 이름을 분석할 수 없습니다.")
        return None

if __name__ == "__main__":
    # --- 2. 필요한 폴더 생성 ---
    os.makedirs(TENSORBOARD_LOG_DIR, exist_ok=True)
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    
    # --- 3. 환경 실행 ---
    # environment.py에 정의된 로봇 팔 환경을 불러옵니다.
    env = RoboticArmEnv()
    
    # --- 4. 콜백 설정 ---
    # 훈련 중 주기적으로 모델을 저장하는 콜백입니다.
    checkpoint_callback = CheckpointCallback(
        save_freq=CHECKPOINT_FREQ,
        save_path=CHECKPOINT_DIR,
        name_prefix=CHECKPOINT_PREFIX,
        save_replay_buffer=True,
        save_vecnormalize=True,
    )
    
    # --- 5. 모델 불러오기 또는 새로 생성하기 ---
    latest_checkpoint = find_latest_checkpoint(CHECKPOINT_DIR, CHECKPOINT_PREFIX)
    
    if latest_checkpoint:
        print(f"✅ 체크포인트에서 훈련을 재개합니다: {latest_checkpoint}")
        # 저장된 모델을 불러옵니다.
        model = PPO.load(
            latest_checkpoint, 
            env=env,
            tensorboard_log=TENSORBOARD_LOG_DIR
        )
        print(f"현재까지 {model.num_timesteps}번 학습되었습니다.")
    else:
        print("🚀 새로운 훈련을 시작합니다.")
        # 새로운 PPO 모델을 생성합니다.
        model = PPO(
            "MlpPolicy",
            env,
            verbose=1,
            tensorboard_log=TENSORBOARD_LOG_DIR,
            n_steps=2048,
            batch_size=64,
            gamma=0.99,
            learning_rate=3e-4,
            ent_coef=0.0,
            clip_range=0.2,
            n_epochs=10,
        )

    # --- 6. 훈련 시작 ---
    # `learn` 함수는 총 TOTAL_TIMESTEPS 만큼 학습을 진행합니다.
    # 만약 모델을 불러왔다면, 남은 횟수만큼만 추가로 학습합니다.
    print(f"총 {TOTAL_TIMESTEPS}번의 타임스텝으로 훈련을 진행합니다...")
    model.learn(
        total_timesteps=TOTAL_TIMESTEPS,
        callback=checkpoint_callback,
        tb_log_name="PPO_RoboticArm",
        # 새로운 훈련일 때만 타임스텝 카운터를 리셋합니다.
        reset_num_timesteps=(latest_checkpoint is None) 
    )
    
    # --- 7. 최종 모델 저장 ---
    model.save(FINAL_MODEL_PATH)
    print(f"🎉 훈련 완료! 최종 모델이 {FINAL_MODEL_PATH}에 저장되었습니다.")

    # 환경 종료
    env.close()
