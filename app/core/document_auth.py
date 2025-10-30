from typing import Dict, Optional
import numpy as np
import cv2


class DocumentAuthenticator:
    """Verify document authenticity"""

    def __init__(self, min_score: float = 60.0):
        self.min_score = min_score

    def check_authenticity(self, image: np.ndarray, structured_data: Optional[Dict] = None) -> Dict:
        """Run all document authenticity checks"""
        results = {}

        results['tampering'] = self._detect_tampering(image)

        if structured_data:
            results['data_consistency'] = self._check_data_consistency(structured_data)
            if expiry := structured_data.get('date_expiration'):
                results['expiry_validation'] = self._validate_expiry_date(expiry)

        checks_passed = sum(
            1 for check in results.values()
            if isinstance(check, dict) and check.get('passed', False)
        )
        total_checks = sum(
            1 for check in results.values()
            if isinstance(check, dict) and 'passed' in check
        )

        authenticity_score = (checks_passed / total_checks * 100) if total_checks > 0 else 50.0
        is_authentic = authenticity_score >= self.min_score

        return {
            'is_authentic': bool(is_authentic),
            'authenticity_score': float(authenticity_score),
            'checks_passed': f"{checks_passed}/{total_checks}",
            'checks': results
        }

    def _detect_tampering(self, image: np.ndarray) -> Dict:
        """Detect document tampering using noise uniformity"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

            h, w = gray.shape
            grid_size = 4
            cell_h, cell_w = h // grid_size, w // grid_size

            noise_levels = []
            for i in range(grid_size):
                for j in range(grid_size):
                    cell = gray[i*cell_h:(i+1)*cell_h, j*cell_w:(j+1)*cell_w]
                    blurred = cv2.GaussianBlur(cell, (5, 5), 0)
                    noise = cv2.absdiff(cell, blurred)
                    noise_levels.append(float(np.std(noise)))

            uniformity = 1.0 - min(np.std(noise_levels) / (np.mean(noise_levels) + 1e-6), 1.0)
            is_tampered = uniformity < 0.7

            return {
                'is_tampered': bool(is_tampered),
                'uniformity': float(uniformity),
                'passed': bool(not is_tampered)
            }
        except Exception as e:
            return {'is_tampered': True, 'passed': False, 'error': str(e)}

    def _check_data_consistency(self, structured_data: Dict) -> Dict:
        """Validate data consistency"""
        issues = []

        try:
            if dob := structured_data.get('date_naissance'):
                try:
                    # Handle different date formats
                    if isinstance(dob, str) and len(dob) == 8:  # YYYYMMDD
                        from datetime import datetime
                        dob_date = datetime.strptime(dob, '%Y%m%d')
                        age = (datetime.now() - dob_date).days / 365.25

                        if age < 0:
                            issues.append('Date of birth is in future')
                        elif age < 16:
                            issues.append('Person under 16')
                        elif age > 120:
                            issues.append('Person over 120')
                except:
                    issues.append('Invalid DOB format')

            is_consistent = len(issues) == 0

            return {
                'is_consistent': bool(is_consistent),
                'issues': issues,
                'passed': bool(is_consistent)
            }
        except Exception as e:
            return {'is_consistent': False, 'issues': [str(e)], 'passed': False}

    def _validate_expiry_date(self, expiry_date_str: str) -> Dict:
        """Validate document expiry"""
        try:
            from datetime import datetime

            date_formats = ['%Y%m%d', '%d%m%Y', '%Y-%m-%d']

            expiry_date = None
            for fmt in date_formats:
                try:
                    expiry_date = datetime.strptime(expiry_date_str, fmt)
                    break
                except ValueError:
                    continue

            if not expiry_date:
                return {'is_valid': False, 'status': 'invalid_format', 'passed': False}

            today = datetime.now()
            is_expired = expiry_date < today
            days_until_expiry = (expiry_date - today).days

            if is_expired:
                status = 'expired'
                is_valid = False
            elif days_until_expiry < 30:
                status = 'expiring_soon'
                is_valid = True
            else:
                status = 'valid'
                is_valid = True

            return {
                'is_valid': bool(is_valid),
                'status': status,
                'days_until_expiry': int(days_until_expiry),
                'passed': bool(is_valid)
            }
        except Exception as e:
            return {'is_valid': False, 'status': 'error', 'passed': False, 'error': str(e)}