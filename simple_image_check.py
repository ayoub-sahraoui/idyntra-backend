import cv2
import numpy as np

# Simple image info check
image_path = "docs/clean_cropped_id/id.jpg"
print(f"📁 Checking: {image_path}\n")

try:
    img = cv2.imread(image_path)
    if img is None:
        print("❌ Failed to load image")
    else:
        h, w = img.shape[:2]
        channels = img.shape[2] if len(img.shape) > 2 else 1
        aspect_ratio = w / h
        
        print(f"✅ Image Info:")
        print(f"   Dimensions: {w} x {h} pixels")
        print(f"   Aspect Ratio: {aspect_ratio:.2f}")
        print(f"   Channels: {channels}")
        print(f"   File Size: {img.nbytes / 1024:.1f} KB (in memory)")
        print()
        
        # Check aspect ratio against document ranges
        is_landscape = 1.2 <= aspect_ratio <= 2.0
        is_portrait = 0.5 <= aspect_ratio <= 0.83
        
        print(f"📐 Aspect Ratio Analysis:")
        print(f"   Landscape range (1.2-2.0): {'✅ YES' if is_landscape else '❌ NO'}")
        print(f"   Portrait range (0.5-0.83): {'✅ YES' if is_portrait else '❌ NO'}")
        
        if not (is_landscape or is_portrait):
            print(f"   ⚠️  Aspect ratio {aspect_ratio:.2f} is outside document ranges!")
            print(f"   This could be why document detection fails.")
        
        # Analyze image content
        print(f"\n🔍 Image Analysis:")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if channels > 1 else img
        
        # Check brightness
        mean_brightness = np.mean(gray)
        print(f"   Brightness: {mean_brightness:.1f}/255 ({'bright' if mean_brightness > 200 else 'dark' if mean_brightness < 50 else 'normal'})")
        
        # Check contrast
        contrast = np.std(gray)
        print(f"   Contrast: {contrast:.1f} ({'low' if contrast < 30 else 'high' if contrast > 80 else 'normal'})")
        
        # Check for edges (document boundary detection)
        edges = cv2.Canny(gray, 50, 150)
        edge_pixels = np.sum(edges > 0)
        edge_ratio = edge_pixels / (w * h)
        print(f"   Edge Pixels: {edge_pixels} ({edge_ratio*100:.1f}% of image)")
        
        if edge_ratio < 0.01:
            print(f"   ⚠️  Very few edges detected - image might be too smooth/processed")
        
except Exception as e:
    print(f"❌ Error: {e}")
