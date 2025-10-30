from typing import Dict
import numpy as np
import cv2
from PIL import Image


class DeepfakeDetector:
    """Deepfake detection using transformer models"""

    def __init__(self, model_name: str = "dima806/deepfake_vs_real_image_detection", use_gpu: bool = False):
        self.model_name = model_name
        self.use_gpu = use_gpu
        self.processor = None
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load the deepfake detection model"""
        try:
            from transformers import AutoImageProcessor, AutoModelForImageClassification
            import torch

            self.processor = AutoImageProcessor.from_pretrained(self.model_name)
            self.model = AutoModelForImageClassification.from_pretrained(self.model_name)

            if self.use_gpu and torch.cuda.is_available():
                self.model = self.model.to('cuda')
                self.device = 'cuda'
            else:
                self.device = 'cpu'

            self.model.eval()
            self.available = True

        except Exception as e:
            self.available = False
            print(f"Deepfake model loading failed: {e}")

    def detect(self, image: np.ndarray) -> Dict:
        """Detect deepfakes in image"""
        if not self.available:
            return {
                'is_real': True,
                'confidence': 0.5,
                'model_available': False
            }

        try:
            import torch

            # Convert to RGB PIL Image
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if len(image.shape) == 3 else image
            if isinstance(rgb_image, np.ndarray):
                pil_image = Image.fromarray(rgb_image)
            else:
                pil_image = rgb_image

            # Process image
            inputs = self.processor(images=pil_image, return_tensors="pt")

            if self.device == 'cuda':
                inputs = {k: v.to('cuda') for k, v in inputs.items()}

            # Run inference
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits

            probs = torch.softmax(logits, dim=1)
            predicted_class = logits.argmax(-1).item()
            confidence = probs[0][predicted_class].item()
            label = self.model.config.id2label[predicted_class]

            is_real = label.lower() == "real"

            return {
                'is_real': bool(is_real),
                'confidence': float(confidence),
                'label': label,
                'model_available': True
            }

        except Exception as e:
            return {
                'is_real': True,
                'confidence': 0.5,
                'error': str(e),
                'model_available': False
            }