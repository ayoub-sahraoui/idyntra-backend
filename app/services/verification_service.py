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
        config,
        logger
    ):
        self.liveness_detector = liveness_detector
        self.face_matcher = face_matcher
        self.doc_checker = doc_checker
        self.deepfake_detector = deepfake_detector
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

        # Run independent checks in parallel
        results = await self._run_parallel_checks(id_document, selfie)

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
            results['liveness_check'] = {'passed': False, 'error': str(e)}
        
        try:
            self.logger.info("Running deepfake check...")
            results['deepfake_check'] = await self._run_deepfake_check(selfie)
            self.logger.info("✓ Deepfake check completed")
        except Exception as e:
            self.logger.exception(f"Deepfake check failed: {e}")
            results['deepfake_check'] = {'passed': False, 'error': str(e)}
        
        try:
            self.logger.info("Running document authenticity check...")
            results['document_authenticity'] = await self._run_document_check(id_document)
            self.logger.info("✓ Document authenticity check completed")
        except Exception as e:
            self.logger.exception(f"Document authenticity check failed: {e}")
            results['document_authenticity'] = {'passed': False, 'error': str(e)}
        
        try:
            self.logger.info("Running face match...")
            results['face_match'] = await self._run_face_match(id_document, selfie)
            self.logger.info("✓ Face match completed")
        except Exception as e:
            self.logger.exception(f"Face match failed: {e}")
            results['face_match'] = {'passed': False, 'error': str(e)}

        return results

    def _make_decision(self, results: Dict) -> Dict:
        """Make final verification decision"""

        # Calculate scores
        liveness_score = results.get('liveness_check', {}).get('liveness_score', 0) * 100
        face_confidence = results.get('face_match', {}).get('confidence', 0)
        auth_score = results.get('document_authenticity', {}).get('authenticity_score', 0)
        deepfake_conf = results.get('deepfake_check', {}).get('confidence', 0.5) * 100

        # Weighted average (adjusted weights for better balance)
        overall = (
            liveness_score * 0.20 +      # 20% - Liveness detection
            face_confidence * 0.40 +     # 40% - Face matching (most important)
            auth_score * 0.20 +          # 20% - Document authenticity
            deepfake_conf * 0.20         # 20% - Deepfake detection
        )

        # Decision logic (adjusted thresholds)
        # >= 80: High confidence, auto-approve
        # >= 60: Medium confidence, manual review recommended
        # < 60: Low confidence, reject
        if overall >= 80:
            status = VerificationStatus.APPROVED
        elif overall >= 60:
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