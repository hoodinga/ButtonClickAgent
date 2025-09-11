import time

# --- 1. Import Environment and SB3 PPO ---
from environment import RoboticArmEnv
from stable_baselines3 import PPO
import pygame

# --- Constants ---
MODEL_PATH = "final_model.zip"
NUM_EPISODES = 1000

if __name__ == "__main__":
    print("--- Starting Agent Evaluation ---")
    
    # --- 2. Instantiate the Environment with Rendering ---
    # We must set render_mode to "human" to visually see the agent play.
    env = RoboticArmEnv(render_mode="human")
    
    # --- 3. Load the Pre-trained Model ---
    try:
        model = PPO.load(MODEL_PATH, env=env)
        print(f"✅ Model loaded successfully from {MODEL_PATH}")
    except FileNotFoundError:
        print(f"❌ Error: Model file not found at {MODEL_PATH}.")
        print("Please run the train.py script first to generate the model.")
        env.close()
        exit()

    # --- 4. Evaluation Loop ---
    for episode in range(NUM_EPISODES):
        print(f"\n--- Starting Episode {episode + 1}/{NUM_EPISODES} ---")
        
        # Reset the environment to get the initial state
        obs, info = env.reset()
        
        terminated = False
        truncated = False
        total_reward = 0.0
        
        # Loop until the episode is finished
        while not (terminated or truncated):
            # Use the model to predict the best action (deterministic=True)
            action, _states = model.predict(obs, deterministic=True)
            
            # Take the action in the environment
            obs, reward, terminated, truncated, info = env.step(action)
            
            # Accumulate the reward
            total_reward += reward
            pygame.event.pump()
            # The render() call is handled within the environment's step method
            # when render_mode is "human", so we don't need to call it here.
            
            # Optional: Add a small delay to make it easier to watch
            time.sleep(0.01)

        print(f"Episode {episode + 1} finished.")
        print(f"Total Reward: {total_reward:.2f}")

    # --- 5. Cleanup ---
    print("\n--- Evaluation finished. Closing environment. ---")
    env.close()

