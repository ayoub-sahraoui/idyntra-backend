from typing import Dict
import asyncio
from concurrent.futures import ThreadPoolExecutor
from enum import Enum


class VerificationStatus(Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"
    ERROR = "error"


class VerificationService:
    """
    Centralized verification service with dependency injection
    This separates business logic from API endpoints
    """

    def __init__(
        self,
        liveness_detector,
        face_matcher,
        doc_checker,
        deepfake_detector,
        similarity_detector,
        document_structure_detector,
        config,
        logger
    ):
        self.liveness_detector = liveness_detector
        self.face_matcher = face_matcher
        self.doc_checker = doc_checker
        self.deepfake_detector = deepfake_detector
        self.similarity_detector = similarity_detector
        self.document_structure_detector = document_structure_detector
        self.config = config
        self.logger = logger

        # Thread pool for CPU-bound tasks
        # Using max_workers=1 to avoid segfaults with face_recognition/dlib threading issues
        self.executor = ThreadPoolExecutor(max_workers=1)

    async def verify_identity(
        self,
        id_document,
        selfie
    ) -> Dict:
        """
        Main verification pipeline with parallel execution where possible
        """

        self.logger.info("Starting verification pipeline")

        # CRITICAL: Check if same image is used for both (fraud detection)
        self.logger.info("Checking for image similarity (duplicate detection)...")
        similarity_check = await self._run_similarity_check(id_document, selfie)
        
        if similarity_check.get('is_duplicate', False):
            self.logger.warning("⚠️ FRAUD ALERT: Same image used for document and selfie!")
            return {
                'status': VerificationStatus.REJECTED.value,
                'overall_confidence': 0.0,
                'message': '❌ Fraud detected: Same image used for both document and selfie',
                'similarity_check': similarity_check,
                'face_match': {
                    'matched': False, 
                    'confidence': 0.0, 
                    'distance': None,
                    'strategy': None,
                    'error': 'Duplicate image detected'
                },
                'liveness_check': {
                    'is_live': False, 
                    'liveness_score': None,
                    'checks_passed': None,
                    'confidence': None,
                    'checks': None,
                    'error': 'Duplicate image detected'
                },
                'deepfake_check': {
                    'is_real': False, 
                    'confidence': None,
                    'label': None,
                    'model_available': None,
                    'error': 'Duplicate image detected'
                },
                'document_authenticity': {
                    'is_authentic': False, 
                    'authenticity_score': None,
                    'checks_passed': None,
                    'checks': None,
                    'error': 'Duplicate image detected'
                }
            }
        
        # Check if document image actually contains a document
        self.logger.info("Validating document structure...")
        doc_structure_check = await self._run_document_structure_check(id_document)
        
        if not doc_structure_check.get('has_document', False):
            self.logger.warning("⚠️ Document validation failed: No document structure detected")
            return {
                'status': VerificationStatus.REJECTED.value,
                'overall_confidence': 0.0,
                'message': '❌ Invalid document: Image does not contain a proper identity document',
                'document_structure': doc_structure_check,
                'similarity_check': similarity_check,
                'face_match': {
                    'matched': False, 
                    'confidence': 0.0, 
                    'distance': None,
                    'strategy': None,
                    'error': 'No document detected'
                },
                'liveness_check': {
                    'is_live': False, 
                    'liveness_score': None,
                    'checks_passed': None,
                    'confidence': None,
                    'checks': None,
                    'error': 'No document detected'
                },
                'deepfake_check': {
                    'is_real': False, 
                    'confidence': None,
                    'label': None,
                    'model_available': None,
                    'error': 'No document detected'
                },
                'document_authenticity': {
                    'is_authentic': False, 
                    'authenticity_score': None,
                    'checks_passed': None,
                    'checks': None,
                    'error': 'No document detected'
                }
            }
        
        # Check if document is just a close-up face
        face_only_check = await self._check_if_just_face(id_document)
        if face_only_check.get('is_just_face', False):
            self.logger.warning("⚠️ Document is just a face photo, not a proper document")
            return {
                'status': VerificationStatus.REJECTED.value,
                'overall_confidence': 0.0,
                'message': '❌ Invalid document: Please provide a full identity document, not just a face photo',
                'document_structure': doc_structure_check,
                'face_only_check': face_only_check,
                'similarity_check': similarity_check,
                'face_match': {
                    'matched': False, 
                    'confidence': 0.0, 
                    'distance': None,
                    'strategy': None,
                    'error': 'Document is just a face'
                },
                'liveness_check': {
                    'is_live': False, 
                    'liveness_score': None,
                    'checks_passed': None,
                    'confidence': None,
                    'checks': None,
                    'error': 'Document is just a face'
                },
                'deepfake_check': {
                    'is_real': False, 
                    'confidence': None,
                    'label': None,
                    'model_available': None,
                    'error': 'Document is just a face'
                },
                'document_authenticity': {
                    'is_authentic': False, 
                    'authenticity_score': None,
                    'checks_passed': None,
                    'checks': None,
                    'error': 'Document is just a face'
                }
            }

        # Run independent checks
        results = await self._run_parallel_checks(id_document, selfie)
        
        # Add pre-checks to results
        results['similarity_check'] = similarity_check
        results['document_structure'] = doc_structure_check

        # Make final decision
        decision = self._make_decision(results)

        response = {
            **decision,
            **results,  # Include individual check results
        }

        return response

    async def _run_parallel_checks(
        self,
        id_document,
        selfie
    ) -> Dict:
        """Run checks sequentially to avoid threading issues with ML libraries"""
        results = {}
        
        # Run checks sequentially (not in parallel) to prevent segfaults
        # face_recognition/dlib and transformers have threading issues
        try:
            self.logger.info("Running liveness check...")
            results['liveness_check'] = await self._run_liveness_check(selfie)
            self.logger.info("✓ Liveness check completed")
        except Exception as e:
            self.logger.exception(f"Liveness check failed: {e}")
            results['liveness_check'] = {
                'is_live': False, 
                'liveness_score': None,
                'checks_passed': None,
                'confidence': None,
                'checks': None,
                'error': str(e)
            }
        
        try:
            self.logger.info("Running deepfake check...")
            results['deepfake_check'] = await self._run_deepfake_check(selfie)
            self.logger.info("✓ Deepfake check completed")
        except Exception as e:
            self.logger.exception(f"Deepfake check failed: {e}")
            results['deepfake_check'] = {
                'is_real': False, 
                'confidence': None,
                'label': None,
                'model_available': None,
                'error': str(e)
            }
        
        try:
            self.logger.info("Running document authenticity check...")
            results['document_authenticity'] = await self._run_document_check(id_document)
            self.logger.info("✓ Document authenticity check completed")
        except Exception as e:
            self.logger.exception(f"Document authenticity check failed: {e}")
            results['document_authenticity'] = {
                'is_authentic': False, 
                'authenticity_score': None,
                'checks_passed': None,
                'checks': None,
                'error': str(e)
            }
        
        try:
            self.logger.info("Running face match...")
            results['face_match'] = await self._run_face_match(id_document, selfie)
            self.logger.info("✓ Face match completed")
        except Exception as e:
            self.logger.exception(f"Face match failed: {e}")
            results['face_match'] = {
                'matched': False, 
                'confidence': 0.0, 
                'distance': None,
                'strategy': None,
                'error': str(e)
            }

        return results

    def _make_decision(self, results: Dict) -> Dict:
        """Make final verification decision"""

        # Calculate scores
        liveness_score = results.get('liveness_check', {}).get('liveness_score', 0) * 100
        face_confidence = results.get('face_match', {}).get('confidence', 0)
        auth_score = results.get('document_authenticity', {}).get('authenticity_score', 0)
        deepfake_conf = results.get('deepfake_check', {}).get('confidence', 0.5) * 100

        # Weighted average (adjusted weights for better balance)
        # Face matching is most reliable, document auth is least reliable for photos
        overall = (
            liveness_score * 0.20 +      # 20% - Liveness detection
            face_confidence * 0.50 +     # 50% - Face matching (most important and reliable)
            auth_score * 0.10 +          # 10% - Document authenticity (reduced, prone to false positives with photos)
            deepfake_conf * 0.20         # 20% - Deepfake detection
        )

        # Decision logic (adjusted thresholds)
        # >= 75: High confidence, auto-approve
        # >= 55: Medium confidence, manual review recommended
        # < 55: Low confidence, reject
        if overall >= 75:
            status = VerificationStatus.APPROVED
        elif overall >= 55:
            status = VerificationStatus.MANUAL_REVIEW
        else:
            status = VerificationStatus.REJECTED

        return {
            'status': status.value,
            'overall_confidence': overall,
            'message': self._get_message(status, overall)
        }

    def _get_message(self, status: VerificationStatus, confidence: float) -> str:
        """Get user-friendly message"""
        if status == VerificationStatus.APPROVED:
            return f"✅ Identity verified (confidence: {confidence:.1f}%)"
        elif status == VerificationStatus.MANUAL_REVIEW:
            return f"⚠️ Manual review required (confidence: {confidence:.1f}%)"
        else:
            return f"❌ Verification failed (confidence: {confidence:.1f}%)"

    async def _run_liveness_check(self, image):
        """Run liveness check in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.liveness_detector.check,
            image
        )

    async def _run_deepfake_check(self, image):
        """Run deepfake check in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.deepfake_detector.detect,
            image
        )

    async def _run_document_check(self, image):
        """Run document check in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.doc_checker.check_authenticity,
            image
        )

    async def _run_face_match(self, id_image, selfie_image):
        """Run face match in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.face_matcher.match_faces,
            id_image,
            selfie_image
        )
    
    async def _run_similarity_check(self, image1, image2):
        """Check if two images are too similar (duplicate detection)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.similarity_detector.are_images_too_similar,
            image1,
            image2
        )
    
    async def _run_document_structure_check(self, image):
        """Check if image contains a proper document structure"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.document_structure_detector.detect_document_structure,
            image
        )
    
    async def _check_if_just_face(self, image):
        """Check if document image is just a close-up face"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.document_structure_detector.is_just_a_face,
            image
        )