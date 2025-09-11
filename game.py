import pygame
import math
import random
import sys

# --- 초기 설정 (Initial Setup) ---
pygame.init()

# --- 상수 (Constants) ---
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Robotic Arm Challenge")

# 시계 (Clock)
CLOCK = pygame.time.Clock()
FPS = 60

# 색상 팔레트 (Color Palette)
COLOR_BACKGROUND = "#F0F4F8"  # 부드러운 배경색 (Soft background color)
COLOR_ARM = "#34495E"         # 로봇 팔 색상 (Robotic arm color)
COLOR_JOINTS = "#E74C3C"      # 관절 및 강조 색상 (Joints and accent color)
COLOR_BUTTON = "#2ECC71"       # 버튼 기본 색상 (Button default color)
COLOR_BUTTON_PRESSED = "#27AE60" # 버튼 눌렸을 때 색상 (Button pressed color)
COLOR_SLIDER_BG = "#BDC3C7"   # 슬라이더 배경색 (Slider background color)
COLOR_SLIDER_HANDLE = "#E74C3C" # 슬라이더 핸들 색상 (Slider handle color)
COLOR_TEXT = "#2C3E50"         # 텍스트 색상 (Text color)
COLOR_PARTICLE = ["#E74C3C", "#F1C40F", "#3498DB", "#2ECC71"] # 파티클 색상 (Particle colors)

# 폰트 (Fonts)
try:
    FONT_MAIN = pygame.font.SysFont("Arial", 48, bold=True)
    FONT_SUB = pygame.font.SysFont("Arial", 24)
except pygame.error:
    # Fallback if system font is not available
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
            # 핸들 위치 업데이트 (Update handle position)
            self.handle_rect.centerx = max(self.rect.left, min(event.pos[0], self.rect.right))
            # 값 업데이트 (Update value)
            ratio = (self.handle_rect.centerx - self.rect.left) / self.rect.width
            self.val = self.min_val + ratio * (self.max_val - self.min_val)

    def draw(self, surface):
        """슬라이더를 화면에 그립니다 (Draws the slider on the screen)"""
        # 슬라이더 트랙 (Slider track)
        pygame.draw.rect(surface, COLOR_SLIDER_BG, self.rect, border_radius=5)
        # 슬라이더 핸들 (Slider handle)
        pygame.draw.rect(surface, COLOR_SLIDER_HANDLE, self.handle_rect, border_radius=7)

# --- 게임 객체 클래스 (Game Object Classes) ---
class RoboticArm:
    """여러 세그먼트로 구성된 로봇 팔 클래스 (A robotic arm class composed of multiple segments)"""
    def __init__(self, base_x, base_y, num_segments, segment_length):
        self.base_pos = (base_x, base_y)
        self.segments = []
        start_pos = self.base_pos
        for _ in range(num_segments):
            segment = {'length': segment_length, 'angle': 0, 'start_pos': start_pos, 'end_pos': start_pos}
            self.segments.append(segment)

    def update(self, angles):
        """슬라이더 값에 따라 팔의 각도와 위치를 업데이트합니다 (Updates arm angles and positions based on slider values)"""
        current_angle = 0
        current_pos = self.base_pos
        for i, segment in enumerate(self.segments):
            segment['angle'] = angles[i]
            # 이전 세그먼트의 각도를 누적합니다 (Accumulate angles from previous segments)
            total_angle = sum(s['angle'] for s in self.segments[:i+1])
            
            segment['start_pos'] = current_pos
            end_x = current_pos[0] + segment['length'] * math.cos(math.radians(total_angle))
            end_y = current_pos[1] + segment['length'] * math.sin(math.radians(total_angle))
            segment['end_pos'] = (end_x, end_y)
            current_pos = segment['end_pos']

    def get_end_effector_pos(self):
        """팔의 끝부분(end-effector) 위치를 반환합니다 (Returns the position of the end-effector)"""
        return self.segments[-1]['end_pos']

    def draw(self, surface):
        """로봇 팔을 그립니다 (Draws the robotic arm)"""
        # 팔 세그먼트 그리기 (Draw arm segments)
        for segment in self.segments:
            pygame.draw.line(surface, COLOR_ARM, segment['start_pos'], segment['end_pos'], 15)

        # 관절 그리기 (Draw joints)
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
            self.animation_scale = 1.5 # 성공 시 '팝' 애니메이션 (Pop animation on success)
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
        # 테두리로 깔끔한 느낌 추가 (Add a border for a cleaner look)
        pygame.draw.circle(surface, tuple(max(0, c-20) for c in color[:3]), self.pos, current_radius, 3)

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
        self.lifespan = random.randint(30, 60) # 프레임 단위 (in frames)

    def update(self):
        """파티클 위치와 수명을 업데이트합니다 (Updates particle position and lifespan)"""
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.1 # 간단한 중력 효과 (Simple gravity effect)
        self.lifespan -= 1
        self.radius -= 0.1

    def draw(self, surface):
        """파티클을 그립니다 (Draws the particle)"""
        if self.lifespan > 0 and self.radius > 0:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(self.radius))


# --- 메인 게임 클래스 (Main Game Class) ---
class Game:
    """게임의 전체 흐름과 상태를 관리하는 메인 클래스 (The main class that manages the overall game flow and state)"""
    def __init__(self):
        self.game_state = "playing"
        self.levels = [
            {'arm': (SCREEN_WIDTH / 2, SCREEN_HEIGHT - 100, 2, 120), 'button': (SCREEN_WIDTH / 2, 150)},
            {'arm': (150, SCREEN_HEIGHT - 50, 3, 90), 'button': (650, 100)},
            {'arm': (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, 4, 70), 'button': (SCREEN_WIDTH-100, SCREEN_HEIGHT-100)},
        ]
        self.current_level = 0
        self.win_timer = 0
        self.particles = []
        self.setup_level()

    def setup_level(self):
        """현재 레벨을 설정합니다 (Sets up the current level)"""
        if self.current_level >= len(self.levels):
            self.game_state = "game_over"
            return
            
        level_data = self.levels[self.current_level]
        arm_config = level_data['arm']
        button_pos = level_data['button']

        self.arm = RoboticArm(arm_config[0], arm_config[1], arm_config[2], arm_config[3])
        self.button = TargetButton(button_pos[0], button_pos[1], 25)
        
        self.sliders = []
        num_sliders = self.arm.segments.__len__()
        slider_y_start = 50
        for i in range(num_sliders):
            slider = Slider(50, slider_y_start + i * 50, 200, 10, -180, 180, 0)
            self.sliders.append(slider)
        
        self.game_state = "playing"
        self.win_timer = 0
        self.particles = []

    def handle_events(self):
        """게임 이벤트를 처리합니다 (Handles game events)"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if self.game_state == "playing":
                for slider in self.sliders:
                    slider.handle_event(event)

            if self.game_state == "win" and event.type == pygame.MOUSEBUTTONDOWN:
                self.current_level += 1
                self.setup_level()
    
    def update(self):
        """게임 상태를 업데이트합니다 (Updates the game state)"""
        if self.game_state == "playing":
            angles = [s.val for s in self.sliders]
            self.arm.update(angles)
            self.button.update()
            
            end_effector_pos = self.arm.get_end_effector_pos()
            if self.button.check_collision(end_effector_pos):
                self.game_state = "win"
                self.win_timer = FPS * 2 # 2초 동안 승리 화면 표시 (Show win screen for 2 seconds)
                # 성공 파티클 생성 (Create success particles)
                for _ in range(50):
                    self.particles.append(Particle(self.button.pos[0], self.button.pos[1]))
        
        elif self.game_state == "win":
            self.button.update()
            self.win_timer -= 1
            if self.win_timer <= 0:
                # 다음 레벨로 넘어갈 준비 (Prepare for the next level)
                # 여기서는 클릭을 기다리도록 설정 (Here, set to wait for a click)
                pass
            
            # 파티클 업데이트 (Update particles)
            for p in self.particles:
                p.update()
            self.particles = [p for p in self.particles if p.lifespan > 0]
            
    def draw(self):
        """모든 게임 요소를 화면에 그립니다 (Draws all game elements on the screen)"""
        SCREEN.fill(COLOR_BACKGROUND)
        
        # UI 그리기 (Draw UI)
        for i, slider in enumerate(self.sliders):
            slider.draw(SCREEN)
            # 슬라이더 라벨 (Slider label)
            label = FONT_SUB.render(f"Joint {i+1}", True, COLOR_TEXT)
            SCREEN.blit(label, (slider.rect.right + 15, slider.rect.centery - 12))
        
        # 게임 객체 그리기 (Draw game objects)
        self.arm.draw(SCREEN)
        self.button.draw(SCREEN)

        # 파티클 그리기 (Draw particles)
        for p in self.particles:
            p.draw(SCREEN)

        # 승리 메시지 (Win message)
        if self.game_state == "win":
            win_text = FONT_MAIN.render("SUCCESS!", True, COLOR_BUTTON_PRESSED)
            text_rect = win_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 50))
            SCREEN.blit(win_text, text_rect)
            
            continue_text = FONT_SUB.render("Click to Continue", True, COLOR_TEXT)
            continue_rect = continue_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 20))
            SCREEN.blit(continue_text, continue_rect)

        # 게임 오버 메시지 (Game over message)
        if self.game_state == "game_over":
            over_text = FONT_MAIN.render("YOU WIN THE GAME!", True, COLOR_TEXT)
            text_rect = over_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
            SCREEN.blit(over_text, text_rect)

        pygame.display.flip()

    def run(self):
        """메인 게임 루프 (Main game loop)"""
        while True:
            self.handle_events()
            self.update()
            self.draw()
            CLOCK.tick(FPS)

# --- 게임 실행 (Run the Game) ---
if __name__ == "__main__":
    game = Game()
    game.run()
