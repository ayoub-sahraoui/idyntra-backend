from PIL import Image
import os

image_path = "docs/clean_cropped_id/id.jpg"
print(f"📁 Checking: {image_path}\n")

try:
    # File info
    file_size = os.path.getsize(image_path)
    print(f"💾 File Size: {file_size / 1024:.1f} KB")
    
    # Load with PIL
    img = Image.open(image_path)
    w, h = img.size
    aspect_ratio = w / h
    
    print(f"\n✅ Image Info:")
    print(f"   Dimensions: {w} x {h} pixels")
    print(f"   Aspect Ratio: {aspect_ratio:.2f}")
    print(f"   Format: {img.format}")
    print(f"   Mode: {img.mode}")
    
    # Check aspect ratio
    is_landscape = 1.2 <= aspect_ratio <= 2.0
    is_portrait = 0.5 <= aspect_ratio <= 0.83
    
    print(f"\n📐 Document Aspect Ratio Check:")
    print(f"   Landscape (1.2-2.0): {'✅ PASS' if is_landscape else '❌ FAIL'}")
    print(f"   Portrait (0.5-0.83): {'✅ PASS' if is_portrait else '❌ FAIL'}")
    
    if not (is_landscape or is_portrait):
        print(f"\n⚠️  PROBLEM IDENTIFIED:")
        print(f"   Aspect ratio {aspect_ratio:.2f} is OUTSIDE document ranges!")
        print(f"   This is why document detection fails.")
        print(f"\n💡 SOLUTION:")
        if aspect_ratio > 2.0:
            print(f"   Image is too wide - might be panoramic or ultra-cropped")
            print(f"   Recommendation: Expand aspect ratio range to {aspect_ratio + 0.5:.1f}")
        elif aspect_ratio < 0.5:
            print(f"   Image is too tall - unusual for documents")
        else:
            print(f"   Image between portrait/landscape ranges")
            print(f"   Recommendation: Accept this range or adjust proportions check")
    else:
        print(f"\n✅ Aspect ratio is acceptable for documents")
        print(f"   Issue must be in other detection checks (edges, text, etc.)")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
