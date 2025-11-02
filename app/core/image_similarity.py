"""
Image similarity detection to prevent same-image attacks
"""
from typing import Dict
import numpy as np
import cv2
from skimage.metrics import structural_similarity as ssim


class ImageSimilarityDetector:
    """Detect if two images are too similar (possible duplicate/fraud)"""
    
    def __init__(self, similarity_threshold: float = 0.95):
        """
        Args:
            similarity_threshold: Images above this similarity are considered duplicates
                                 0.95 = 95% similar (very strict)
        """
        self.similarity_threshold = similarity_threshold
    
    def are_images_too_similar(self, image1: np.ndarray, image2: np.ndarray) -> Dict:
        """
        Check if two images are suspiciously similar
        
        Returns:
            Dict with:
                - is_duplicate: bool - True if images are too similar
                - similarity_score: float - 0-1, how similar they are
                - method: str - detection method used
                - passed: bool - False if duplicate detected
        """
        try:
            # Resize both images to same size for comparison
            size = (256, 256)
            img1_resized = cv2.resize(image1, size)
            img2_resized = cv2.resize(image2, size)
            
            # Convert to grayscale
            if len(img1_resized.shape) == 3:
                img1_gray = cv2.cvtColor(img1_resized, cv2.COLOR_BGR2GRAY)
            else:
                img1_gray = img1_resized
                
            if len(img2_resized.shape) == 3:
                img2_gray = cv2.cvtColor(img2_resized, cv2.COLOR_BGR2GRAY)
            else:
                img2_gray = img2_resized
            
            # Method 1: Structural Similarity Index (SSIM)
            ssim_score = ssim(img1_gray, img2_gray)
            
            # Method 2: Histogram comparison
            hist1 = cv2.calcHist([img1_resized], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
            hist1 = cv2.normalize(hist1, hist1).flatten()
            
            hist2 = cv2.calcHist([img2_resized], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
            hist2 = cv2.normalize(hist2, hist2).flatten()
            
            hist_score = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
            
            # Method 3: Pixel-wise difference
            pixel_diff = np.mean(np.abs(img1_gray.astype(float) - img2_gray.astype(float)))
            pixel_similarity = 1.0 - (pixel_diff / 255.0)
            
            # Method 4: Hash comparison (perceptual hash)
            hash1 = self._perceptual_hash(img1_gray)
            hash2 = self._perceptual_hash(img2_gray)
            hash_similarity = 1.0 - (np.sum(hash1 != hash2) / len(hash1))
            
            # Combine scores (weighted average)
            combined_score = (
                ssim_score * 0.40 +         # Most reliable
                hist_score * 0.25 +
                pixel_similarity * 0.20 +
                hash_similarity * 0.15
            )
            
            is_duplicate = combined_score >= self.similarity_threshold
            
            return {
                'is_duplicate': bool(is_duplicate),
                'similarity_score': float(combined_score),
                'details': {
                    'ssim': float(ssim_score),
                    'histogram': float(hist_score),
                    'pixel_similarity': float(pixel_similarity),
                    'hash_similarity': float(hash_similarity)
                },
                'method': 'multi-method',
                'passed': bool(not is_duplicate),
                'threshold_used': self.similarity_threshold
            }
            
        except Exception as e:
            return {
                'is_duplicate': False,
                'similarity_score': 0.0,
                'error': str(e),
                'passed': True  # Fail open - don't block if check fails
            }
    
    def _perceptual_hash(self, image: np.ndarray, hash_size: int = 8) -> np.ndarray:
        """
        Compute perceptual hash (pHash) of an image
        Similar images will have similar hashes
        """
        # Resize to hash_size + 1
        resized = cv2.resize(image, (hash_size + 1, hash_size))
        
        # Compute differences
        diff = resized[:, 1:] > resized[:, :-1]
        
        # Convert to binary hash
        return diff.flatten()
    
    def check_image_uniqueness(self, images: list) -> Dict:
        """
        Check if all images in a list are unique
        Useful for batch verification
        """
        if len(images) < 2:
            return {'all_unique': True, 'duplicates_found': []}
        
        duplicates = []
        for i in range(len(images)):
            for j in range(i + 1, len(images)):
                result = self.are_images_too_similar(images[i], images[j])
                if result['is_duplicate']:
                    duplicates.append({
                        'pair': (i, j),
                        'similarity': result['similarity_score']
                    })
        
        return {
            'all_unique': len(duplicates) == 0,
            'duplicates_found': duplicates,
            'total_comparisons': len(images) * (len(images) - 1) // 2
        }
