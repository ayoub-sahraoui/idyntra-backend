#!/usr/bin/env python3
"""
Diagnose why clean_cropped_id fails document detection
"""
import cv2
import numpy as np
from pathlib import Path
from app.core.document_detection import DocumentStructureDetector

# Load the image
image_path = Path("docs/clean_cropped_id/id.jpg")
if not image_path.exists():
    print(f"❌ Image not found: {image_path}")
    exit(1)

print(f"📁 Loading image: {image_path}")
image = cv2.imread(str(image_path))

if image is None:
    print("❌ Failed to load image")
    exit(1)

print(f"✅ Image loaded successfully")
print(f"   Resolution: {image.shape[1]}x{image.shape[0]}")
print(f"   Channels: {image.shape[2] if len(image.shape) > 2 else 1}")
print()

# Run document detection
print("🔍 Running document structure detection...")
detector = DocumentStructureDetector()
result = detector.detect_document_structure(image)

print("\n" + "="*80)
print("📊 DETECTION RESULTS")
print("="*80)
print(f"Has Document: {result['has_document']}")
print(f"Confidence: {result['confidence']:.2f}")
print(f"Threshold: {result['threshold_used']:.2f}")
print(f"Passed: {result['passed']}")
print()

print("🔎 DETAILED FEATURES:")
print("-"*80)

features = result.get('features_detected', {})

# Card Edges
card_edges = features.get('card_edges', {})
print(f"\n1️⃣  Card Edges Detection:")
print(f"   Detected: {card_edges.get('detected', False)}")
print(f"   Rectangles Found: {card_edges.get('rectangles_found', 0)}")
if card_edges.get('details'):
    print(f"   Details: {card_edges.get('details')}")
if card_edges.get('error'):
    print(f"   ⚠️  Error: {card_edges.get('error')}")

# Text Regions
text_regions = features.get('text_regions', {})
print(f"\n2️⃣  Text Regions Detection:")
print(f"   Has Text Regions: {text_regions.get('has_text_regions', False)}")
print(f"   Text Regions Count: {text_regions.get('text_regions_count', 0)}")
if text_regions.get('error'):
    print(f"   ⚠️  Error: {text_regions.get('error')}")

# Security Features
security = features.get('security_features', {})
print(f"\n3️⃣  Security Features Detection:")
print(f"   Detected: {security.get('detected', False)}")
if 'shiny_ratio' in security:
    print(f"   Shiny Ratio: {security.get('shiny_ratio', 0):.4f}")
    print(f"   Shiny Pixels: {security.get('shiny_pixels', 0)}")
if security.get('reason'):
    print(f"   Reason: {security.get('reason')}")
if security.get('error'):
    print(f"   ⚠️  Error: {security.get('error')}")

# Photo Region
photo = features.get('photo_region', {})
print(f"\n4️⃣  Photo Region Detection:")
print(f"   Detected: {photo.get('detected', False)}")
print(f"   Photo Candidates: {photo.get('photo_candidates', 0)}")
if photo.get('error'):
    print(f"   ⚠️  Error: {photo.get('error')}")

# Proportions
proportions = features.get('proportions', {})
print(f"\n5️⃣  Document Proportions:")
print(f"   Is Document Sized: {proportions.get('is_document_sized', False)}")
if 'aspect_ratio' in proportions:
    print(f"   Aspect Ratio: {proportions.get('aspect_ratio', 0):.2f}")
    print(f"   Dimensions: {proportions.get('width', 0)}x{proportions.get('height', 0)}")
    print(f"   Orientation: {proportions.get('orientation', 'unknown')}")
if proportions.get('error'):
    print(f"   ⚠️  Error: {proportions.get('error')}")

print("\n" + "="*80)
print("💡 ANALYSIS")
print("="*80)

# Calculate what passed
checks_passed = []
checks_failed = []

if card_edges.get('detected'):
    checks_passed.append("Card edges")
else:
    checks_failed.append("Card edges")

if text_regions.get('has_text_regions'):
    checks_passed.append("Text regions")
else:
    checks_failed.append("Text regions")

if security.get('detected'):
    checks_passed.append("Security features")
else:
    checks_failed.append("Security features")

if photo.get('detected'):
    checks_passed.append("Photo region")
else:
    checks_failed.append("Photo region")

if proportions.get('is_document_sized'):
    checks_passed.append("Document proportions")
else:
    checks_failed.append("Document proportions")

print(f"\n✅ Passed Checks ({len(checks_passed)}/5): {', '.join(checks_passed) if checks_passed else 'None'}")
print(f"❌ Failed Checks ({len(checks_failed)}/5): {', '.join(checks_failed) if checks_failed else 'None'}")

print(f"\n📊 Confidence Calculation:")
print(f"   Threshold needed: {result['threshold_used']:.2f} (25%)")
print(f"   Actual confidence: {result['confidence']:.2f}")
print(f"   Gap: {(result['threshold_used'] - result['confidence']):.2f}")

if result['has_document']:
    print(f"\n✅ VERDICT: Document detected!")
else:
    print(f"\n❌ VERDICT: Document NOT detected")
    print(f"\n💡 RECOMMENDATIONS:")
    if not card_edges.get('detected'):
        print(f"   • Image may be too cropped - no visible card edges")
    if not text_regions.get('has_text_regions'):
        print(f"   • Need at least 2 text regions - found {text_regions.get('text_regions_count', 0)}")
    if not proportions.get('is_document_sized'):
        print(f"   • Aspect ratio {proportions.get('aspect_ratio', 0):.2f} outside document range")
    print(f"   • Try lowering threshold from 0.25 to 0.20 or 0.15")

print("\n" + "="*80)
