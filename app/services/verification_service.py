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
        self.executor = ThreadPoolExecutor(max_workers=4)

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
        """Run independent checks in parallel"""
        # Create coroutines for independent operations
        tasks = {
            'liveness_check': self._run_liveness_check(selfie),
            'deepfake_check': self._run_deepfake_check(selfie),
            'document_authenticity': self._run_document_check(id_document),
            'face_match': self._run_face_match(id_document, selfie)
        }

        # Run them concurrently and collect results
        names = list(tasks.keys())
        coros = list(tasks.values())

        gathered = await asyncio.gather(*coros, return_exceptions=True)

        results = {}
        for name, res in zip(names, gathered):
            if isinstance(res, Exception):
                self.logger.exception(f"{name} check failed: {res}")
                results[name] = {'passed': False, 'error': str(res)}
            else:
                results[name] = res

        return results

    def _make_decision(self, results: Dict) -> Dict:
        """Make final verification decision"""

        # Calculate scores
        liveness_score = results.get('liveness_check', {}).get('liveness_score', 0) * 100
        face_confidence = results.get('face_match', {}).get('confidence', 0)
        auth_score = results.get('document_authenticity', {}).get('authenticity_score', 0)
        deepfake_conf = results.get('deepfake_check', {}).get('confidence', 0.5) * 100

        # Weighted average
        overall = (
            liveness_score * 0.25 +
            face_confidence * 0.35 +
            auth_score * 0.25 +
            deepfake_conf * 0.15
        )

        # Decision logic
        if overall >= 85:
            status = VerificationStatus.APPROVED
        elif overall >= 70:
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