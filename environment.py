import pygame
import math
import random
import sys
import numpy as np
import gymnasium as gym
from gymnasium import spaces

# --- Part 1: Original Pygame Game Code ---
# The following code is the original game logic from 'game.py'.
# It has been slightly modified to better integrate with the Gym environment,
# primarily by removing the main game loop and letting the environment control updates.

# --- 초기 설정 (Initial Setup) ---
pygame.init()

# --- 상수 (Constants) ---
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
# Note: The screen is managed by the environment, so direct initialization is handled there.

# 시계 (Clock)
CLOCK = pygame.time.Clock()
FPS = 60

# 색상 팔레트 (Color Palette) - Hex strings are converted to pygame.Color objects for calculations
COLOR_BACKGROUND = pygame.Color("#F0F4F8")
COLOR_ARM = pygame.Color("#34495E")
COLOR_JOINTS = pygame.Color("#E74C3C")
COLOR_BUTTON = pygame.Color("#2ECC71")
COLOR_BUTTON_PRESSED = pygame.Color("#27AE60")
COLOR_SLIDER_BG = pygame.Color("#BDC3C7")
COLOR_SLIDER_HANDLE = pygame.Color("#E74C3C")
COLOR_TEXT = pygame.Color("#2C3E50")
COLOR_PARTICLE = [pygame.Color(c) for c in ["#E74C3C", "#F1C40F", "#3498DB", "#2ECC71"]]


# 폰트 (Fonts)
try:
    FONT_MAIN = pygame.font.SysFont("Arial", 48, bold=True)
    FONT_SUB = pygame.font.SysFont("Arial", 24)
except pygame.error:
    FONT_MAIN = pygame.font.Font(None, 60)
    FONT_SUB = pygame.font.Font(None, 32)


# --- UI 클래스: 슬라이더 (UI Class: Slider) ---
class Slider:
    """각도 조절을 위한 UI 슬라이더 클래스 (A UI slider class to control angles)"""
    def __init__(self, x, y, width, height, min_val, max_val, initial_val):
        self.rect = pygame.Rect(x, y, width, height)
        self.min_val = min_val
        self.max_val = max_val
        self.val = initial_val
        self.handle_width = 20
        self.handle_rect = pygame.Rect(0, y - 5, self.handle_width, height + 10)
        self.update_handle_pos()
        self.is_dragging = False

    def update_handle_pos(self):
        """값에 따라 핸들 위치를 업데이트합니다 (Updates handle position based on value)"""
        if (self.max_val - self.min_val) == 0:
            ratio = 0
        else:
            ratio = (self.val - self.min_val) / (self.max_val - self.min_val)
        self.handle_rect.centerx = self.rect.x + ratio * self.rect.width

    def handle_event(self, event):
        """마우스 이벤트를 처리합니다 (Handles mouse events)"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.handle_rect.collidepoint(event.pos) or self.rect.collidepoint(event.pos):
                self.is_dragging = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.is_dragging = False
        elif event.type == pygame.MOUSEMOTION and self.is_dragging:
            self.handle_rect.centerx = max(self.rect.left, min(event.pos[0], self.rect.right))
            ratio = (self.handle_rect.centerx - self.rect.left) / self.rect.width
            self.val = self.min_val + ratio * (self.max_val - self.min_val)

    def draw(self, surface):
        """슬라이더를 화면에 그립니다 (Draws the slider on the screen)"""
        pygame.draw.rect(surface, COLOR_SLIDER_BG, self.rect, border_radius=5)
        pygame.draw.rect(surface, COLOR_SLIDER_HANDLE, self.handle_rect, border_radius=7)

# --- 게임 객체 클래스 (Game Object Classes) ---
class RoboticArm:
    """여러 세그먼트로 구성된 로봇 팔 클래스 (A robotic arm class composed of multiple segments)"""
    def __init__(self, base_x, base_y, num_segments, segment_length):
        self.base_pos = (base_x, base_y)
        self.num_segments = num_segments
        self.segment_length = segment_length
        self.segments = []
        start_pos = self.base_pos
        for _ in range(num_segments):
            segment = {'length': segment_length, 'angle': 0, 'start_pos': start_pos, 'end_pos': start_pos}
            self.segments.append(segment)

    def update(self, angles):
        """슬라이더 값에 따라 팔의 각도와 위치를 업데이트합니다 (Updates arm angles and positions based on slider values)"""
        current_pos = self.base_pos
        for i, segment in enumerate(self.segments):
            segment['angle'] = angles[i]
            total_angle = sum(s['angle'] for s in self.segments[:i+1])
            
            segment['start_pos'] = current_pos
            end_x = current_pos[0] + segment['length'] * math.cos(math.radians(total_angle))
            end_y = current_pos[1] - segment['length'] * math.sin(math.radians(total_angle)) # Flipped Y for Pygame
            segment['end_pos'] = (end_x, end_y)
            current_pos = segment['end_pos']

    def get_end_effector_pos(self):
        """팔의 끝부분(end-effector) 위치를 반환합니다 (Returns the position of the end-effector)"""
        return self.segments[-1]['end_pos']

    def draw(self, surface):
        """로봇 팔을 그립니다 (Draws the robotic arm)"""
        for segment in self.segments:
            pygame.draw.line(surface, COLOR_ARM, segment['start_pos'], segment['end_pos'], 15)
        pygame.draw.circle(surface, COLOR_JOINTS, self.base_pos, 12)
        for segment in self.segments:
            pygame.draw.circle(surface, COLOR_JOINTS, segment['end_pos'], 8)
            pygame.draw.circle(surface, COLOR_ARM, segment['start_pos'], 12)

class TargetButton:
    """플레이어가 눌러야 하는 목표 버튼 클래스 (The target button class that the player needs to press)"""
    def __init__(self, x, y, radius):
        self.pos = (x, y)
        self.radius = radius
        self.is_pressed = False
        self.animation_scale = 1.0
        self.animation_speed = 0.2

    def check_collision(self, point):
        """주어진 점과 버튼의 충돌을 확인합니다 (Checks collision between a given point and the button)"""
        if self.is_pressed:
            return False
        dist_sq = (point[0] - self.pos[0])**2 + (point[1] - self.pos[1])**2
        if dist_sq < self.radius**2:
            self.is_pressed = True
            self.animation_scale = 1.5
            return True
        return False

    def update(self):
        """버튼 애니메이션을 업데이트합니다 (Updates the button animation)"""
        if self.is_pressed and self.animation_scale > 1.0:
            self.animation_scale -= self.animation_speed
        else:
            self.animation_scale = max(1.0, self.animation_scale)

    def draw(self, surface):
        """버튼을 그립니다 (Draws the button)"""
        color = COLOR_BUTTON_PRESSED if self.is_pressed else COLOR_BUTTON
        current_radius = int(self.radius * self.animation_scale)
        pygame.draw.circle(surface, color, self.pos, current_radius)
        # 테두리 색상 계산을 위해 수정된 부분 (This part is fixed)
        border_color = tuple(max(0, c - 20) for c in color[:3])
        pygame.draw.circle(surface, border_color, self.pos, current_radius, 3)

class Particle:
    """성공 시 나타나는 파티클 효과 클래스 (Particle effect class for success)"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = random.randint(3, 8)
        self.color = random.choice(COLOR_PARTICLE)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1, 5)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.lifespan = random.randint(30, 60)
        self.gravity = 0.1

    def update(self):
        """파티클 위치와 수명을 업데이트합니다 (Updates particle position and lifespan)"""
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.lifespan -= 1
        self.radius -= 0.1

    def draw(self, surface):
        """파티클을 그립니다 (Draws the particle)"""
        if self.lifespan > 0 and self.radius > 0:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(self.radius))

# --- 메인 게임 클래스 (Main Game Class) ---
class Game:
    """게임의 전체 흐름과 상태를 관리하는 메인 클래스 (The main class that manages the overall game flow and state)"""
    def __init__(self, screen=None):
        self.screen = screen
        self.game_state = "playing"
        # --- [수정] 레벨 설정 변경: 로봇 팔을 중앙에 배치하고 버튼 위치는 동적으로 생성 ---
        self.levels = [
            # 각 레벨은 (팔 기본 x, y, 팔 마디 수, 팔 마디 길이) 정보만 가짐
            {'arm_config': (SCREEN_WIDTH / 2, SCREEN_HEIGHT, 2, 120)},
            {'arm_config': (SCREEN_WIDTH / 2, SCREEN_HEIGHT, 3, 90)},
            {'arm_config': (SCREEN_WIDTH / 2, SCREEN_HEIGHT, 4, 70)},
        ]
        self.current_level_index = 0
        self.win_timer = 0
        self.particles = []
        self.setup_level()

    def setup_level(self):
        """현재 레벨을 설정하고, 팔이 닿는 범위 내에 버튼을 무작위로 생성합니다."""
        if self.current_level_index >= len(self.levels):
            self.game_state = "game_over"
            return
            
        level_data = self.levels[self.current_level_index]
        arm_config = level_data['arm_config']

        # 로봇 팔 생성
        self.arm = RoboticArm(arm_config[0], arm_config[1], arm_config[2], arm_config[3])
        
        # --- [수정] 버튼 위치를 무작위로 생성하는 로직 ---
        max_reach = self.arm.num_segments * self.arm.segment_length
        min_reach = max_reach * 0.3  # 너무 가까이 생성되지 않도록 최소 거리 설정
        base_pos = self.arm.base_pos
        
        while True:
            # 화면 내에서 무작위 위치 후보 생성
            button_x = random.uniform(50, SCREEN_WIDTH - 50)
            button_y = random.uniform(50, SCREEN_HEIGHT - 150) # 화면 상단 쪽에 생성되도록 유도
            
            # 로봇 팔 받침대와의 거리 계산
            distance = math.sqrt((button_x - base_pos[0])**2 + (button_y - base_pos[1])**2)
            
            # 거리가 로봇 팔의 최대/최소 도달 범위 내에 있는지 확인
            if min_reach < distance < (max_reach * 0.95): # 닿을 수 있는 거리보다 살짝 안쪽에 생성
                button_pos = (button_x, button_y)
                break # 유효한 위치를 찾으면 루프 종료
                
        self.button = TargetButton(button_pos[0], button_pos[1], 25)
        
        # Sliders are now controlled by the RL agent, but we can keep them for visualization
        self.sliders = []
        num_sliders = self.arm.segments.__len__()
        slider_y_start = 50
        for i in range(num_sliders):
            slider = Slider(50, slider_y_start + i * 50, 200, 10, -180, 180, 0)
            self.sliders.append(slider)
        
        self.game_state = "playing"
        self.win_timer = 0
        self.particles = []

    def handle_events_for_human(self):
        """Allows human interaction for debugging/visualization."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if self.game_state == "playing":
                for slider in self.sliders:
                    slider.handle_event(event)
        return True

    def update_game_state(self, angles=None):
        """게임 상태를 업데이트합니다 (Updates the game state)"""
        if angles is None:
            # If no angles from agent, use sliders (for human play)
            angles = [s.val for s in self.sliders]
        
        # Sync sliders with agent's angles for visualization
        for i, angle in enumerate(angles):
            if i < len(self.sliders):
                self.sliders[i].val = angle
                self.sliders[i].update_handle_pos()

        if self.game_state == "playing":
            self.arm.update(angles)
            self.button.update()
            
            end_effector_pos = self.arm.get_end_effector_pos()
            if self.button.check_collision(end_effector_pos):
                self.game_state = "win"
                self.win_timer = FPS * 2
                for _ in range(50):
                    self.particles.append(Particle(self.button.pos[0], self.button.pos[1]))
        
        elif self.game_state == "win":
            self.button.update()
            self.win_timer -= 1
            if self.win_timer <= 0:
                self.current_level_index += 1
                self.setup_level()

        # Update particles regardless of state
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.lifespan > 0]

    def draw_elements(self):
        """모든 게임 요소를 화면에 그립니다 (Draws all game elements on the screen)"""
        if self.screen is None: return

        self.screen.fill(COLOR_BACKGROUND)
        
        for i, slider in enumerate(self.sliders):
            slider.draw(self.screen)
            label = FONT_SUB.render(f"Joint {i+1}", True, COLOR_TEXT)
            self.screen.blit(label, (slider.rect.right + 15, slider.rect.centery - 12))
        
        self.arm.draw(self.screen)
        self.button.draw(self.screen)

        for p in self.particles:
            p.draw(self.screen)

        if self.game_state == "game_over":
            over_text = FONT_MAIN.render("ALL LEVELS COMPLETE!", True, COLOR_TEXT)
            text_rect = over_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
            self.screen.blit(over_text, text_rect)

        pygame.display.flip()

# --- Part 2: Gymnasium Environment Wrapper ---
# This class wraps the Pygame logic into a standard RL environment.

class RoboticArmEnv(gym.Env):
    """
    A custom Gymnasium environment for the Robotic Arm Challenge game.

    The agent's goal is to control the angles of the robotic arm's joints
    to touch the target button with its end-effector.
    """
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": FPS}

    def __init__(self, render_mode=None, max_steps=500):
        super().__init__()
        
        self.render_mode = render_mode
        self.max_steps_per_episode = max_steps
        self.screen = None
        self.clock = None

        if self.render_mode == "human":
            pygame.init()
            pygame.display.set_caption("Robotic Arm Challenge - RL Agent")
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            self.clock = pygame.time.Clock()

        # The game instance is created here
        self.game = Game(screen=self.screen)
        
        # The number of joints can change per level. We design the spaces
        # for the most complex level (4 joints) and pad observations/actions.
        self.max_joints = 4
        self.angle_step_size = 5.0  # Degrees to change per discrete action

        ### 1. Action Space Definition
        num_actions = 1 + self.max_joints * 2
        self.action_space = spaces.Discrete(num_actions)

        ### 2. Observation Space Definition
        obs_dim = self.max_joints + 2 + 2 + 2 
        self.observation_space = spaces.Box(
            low=-1.0, high=1.0, shape=(obs_dim,), dtype=np.float32
        )

    def _get_obs(self):
        """Constructs the observation numpy array from the current game state."""
        arm = self.game.arm
        button = self.game.button
        
        angles = [seg['angle'] for seg in arm.segments]
        padded_angles = angles + [0.0] * (self.max_joints - len(angles))
        norm_angles = np.array(padded_angles) / 180.0

        end_effector_pos = np.array(arm.get_end_effector_pos(), dtype=np.float32)
        norm_end_effector_pos = self._normalize_coords(end_effector_pos)

        target_pos = np.array(button.pos, dtype=np.float32)
        norm_target_pos = self._normalize_coords(target_pos)

        vector_to_target = target_pos - end_effector_pos
        norm_vector = np.array([vector_to_target[0] / SCREEN_WIDTH, vector_to_target[1] / SCREEN_HEIGHT], dtype=np.float32)

        return np.concatenate([
            norm_angles,
            norm_end_effector_pos,
            norm_target_pos,
            norm_vector
        ]).astype(np.float32)

    def _get_info(self):
        """Returns auxiliary diagnostic information."""
        dist = np.linalg.norm(
            np.array(self.game.arm.get_end_effector_pos()) - np.array(self.game.button.pos)
        )
        return {"distance_to_target": dist}
        
    def _normalize_coords(self, coords):
        """Normalizes (x, y) coordinates from screen space to [-1, 1]."""
        return np.array([
            2 * (coords[0] / SCREEN_WIDTH) - 1,
            2 * (coords[1] / SCREEN_HEIGHT) - 1
        ], dtype=np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        self.game.current_level_index = 0
        self.game.setup_level()
        self.current_step = 0

        observation = self._get_obs()
        info = self._get_info()
        
        return observation, info

    def step(self, action):
        self.current_step += 1
        
        prev_info = self._get_info()
        prev_dist = prev_info["distance_to_target"]

        current_angles = [s['angle'] for s in self.game.arm.segments]
        num_active_joints = len(current_angles)

        if action > 0:
            joint_index = (action - 1) // 2
            direction = 1 if (action - 1) % 2 == 0 else -1
            
            if joint_index < num_active_joints:
                current_angles[joint_index] += direction * self.angle_step_size
                current_angles[joint_index] = max(-180.0, min(180.0, current_angles[joint_index]))

        self.game.update_game_state(angles=current_angles)

        terminated = self.game.button.is_pressed
        truncated = self.current_step >= self.max_steps_per_episode
        
        reward = 0
        current_dist = self._get_info()["distance_to_target"]

        reward += (prev_dist - current_dist) * 0.1
        reward -= 0.01 

        if terminated:
            reward += 200

        if truncated:
            reward -= 5 

        observation = self._get_obs()
        info = self._get_info()

        if self.render_mode == "human":
            self.render()

        return observation, reward, terminated, truncated, info

    def render(self):
        if self.render_mode is None:
            gym.logger.warn(
                "You are calling render method without specifying any render mode. "
                "You can specify the render_mode at initialization, "
                "e.g. gym.make(spec, render_mode='human')"
            )
            return

        if self.render_mode == "human":
            self.game.draw_elements()
            self.clock.tick(self.metadata["render_fps"])
        elif self.render_mode == "rgb_array":
            temp_screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            self.game.screen = temp_screen
            self.game.draw_elements()
            return np.transpose(pygame.surfarray.array3d(temp_screen), axes=(1, 0, 2))

    def close(self):
        if self.screen is not None:
            pygame.display.quit()
            pygame.quit()
            self.screen = None


# --- Part 3: Example Usage ---
if __name__ == "__main__":
    
    env = RoboticArmEnv(render_mode="human")
    
    from gymnasium.utils.env_checker import check_env
    try:
        check_env(RoboticArmEnv())
        print("✅ Environment passed the Gymnasium check.")
    except Exception as e:
        print(f"❌ Environment failed the Gymnasium check: {e}")

    print("\n--- Running a random agent for 2 episodes ---")
    for episode in range(2):
        obs, info = env.reset()
        terminated = False
        truncated = False
        total_reward = 0
        steps = 0
        
        while not (terminated or truncated):
            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            steps += 1
        
        print(f"Episode {episode + 1}: Finished in {steps} steps. Total reward: {total_reward:.2f}")

    env.close()
    print("\n--- Environment closed ---")

