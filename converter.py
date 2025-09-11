import torch
import onnx
import onnxruntime
import numpy as np
import os
from stable_baselines3 import PPO

from environment import RoboticArmEnv

MODEL_PATH = "final_model.zip"
ONNX_MODEL_PATH = "model.onnx"

# --- PolicyWrapper: logits만 반환하도록 래핑 ---
class PolicyWrapper(torch.nn.Module):
    def __init__(self, policy):
        super().__init__()
        self.policy = policy
    def forward(self, x):
        # 정책 네트워크만 직접 호출 (mlp_extractor 이후 policy_net)
        latent_pi, _ = self.policy.mlp_extractor(self.policy.features_extractor(x))
        logits = self.policy.action_net(latent_pi)
        print("PolicyWrapper.forward() - logits shape:", logits.shape)
        return logits
def convert_and_verify():
    print(f"Loading trained model from: {MODEL_PATH}")
    try:
        model = PPO.load(MODEL_PATH, custom_objects={"env": RoboticArmEnv})
    except Exception as e:
        print(f"Error loading model: {e}")
        print("Please ensure 'final_model.zip' exists and was trained with the provided environment.")
        return

    # PolicyWrapper로 감싸서 logits만 반환하도록 함
    pytorch_model = PolicyWrapper(model.policy)
    pytorch_model.eval()

    print("Model loaded successfully.")

    env = RoboticArmEnv()
    obs_space = env.observation_space

    dummy_input = torch.tensor(
        obs_space.sample(),
        dtype=torch.float32
    ).unsqueeze(0)
    print("Dummy input shape:", dummy_input.shape)
    pytorch_logits = pytorch_model(dummy_input)
    print("PyTorch logits shape:", pytorch_logits.shape)
    print("PyTorch logits:", pytorch_logits.detach().numpy())

    print(f"Exporting model to ONNX at: {ONNX_MODEL_PATH}")
    try:
        torch.onnx.export(
            pytorch_model,
            dummy_input,
            ONNX_MODEL_PATH,
            input_names=['observation'],
            output_names=['action'],
            opset_version=12,
            dynamic_axes={
                'observation': {0: 'batch_size'},
                'action': {0: 'batch_size'}
            }
        )
        print("✅ Model exported successfully.")
    except Exception as e:
        print(f"❌ Error during ONNX export: {e}")
        return

    print("\n--- Verifying the ONNX model ---")
    try:
        onnx_model = onnx.load(ONNX_MODEL_PATH)
        onnx.checker.check_model(onnx_model)
        print("✅ ONNX model check passed.")

        ort_session = onnxruntime.InferenceSession(ONNX_MODEL_PATH)
        print("✅ ONNX Runtime session created successfully.")

        ort_inputs = {ort_session.get_inputs()[0].name: dummy_input.numpy()}
        ort_outs = ort_session.run(None, ort_inputs)
        print(f"✅ Inference with ONNX Runtime successful.")
        print("ONNX output shape:", ort_outs[0].shape)
        print("ONNX output:", ort_outs[0])
        print("\nVerification complete. The ONNX model is ready to use.")

    except Exception as e:
        print(f"❌ Error during ONNX model verification: {e}")

    env.close()

if __name__ == "__main__":
    if not os.path.exists(MODEL_PATH):
        print(f"Error: Trained model '{MODEL_PATH}' not found.")
        print("Please run train.py to generate the model first.")
    else:
        convert_and_verify()