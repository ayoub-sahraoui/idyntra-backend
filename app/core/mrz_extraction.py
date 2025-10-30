import os
import tempfile
import cv2
import numpy as np
from typing import Dict, Optional, List, Tuple
import logging
import re
from datetime import datetime

logger = logging.getLogger("idv_api")

class MRZExtractor:
    """Universal MRZ extraction with comprehensive preprocessing and attribute extraction"""

    def __init__(self):
        tessdata_path = os.environ.get('TESSDATA_PREFIX', '/usr/share/tesseract-ocr/4/tessdata')
        os.environ['TESSDATA_PREFIX'] = tessdata_path
        self.tessdata_path = tessdata_path
        
        if os.path.exists(self.tessdata_path):
            logger.info(f"✓ Tesseract data path: {self.tessdata_path}")
        else:
            logger.warning(f"Tesseract data not found at {self.tessdata_path}")

        self.engines = self._check_engines()
        self.engine = next((k for k, v in self.engines.items() if v), None)

    def _check_engines(self) -> Dict[str, bool]:
        """Check which MRZ engines are available"""
        engines = {}
        
        try:
            from readmrz import MrzDetector, MrzReader
            engines['readmrz'] = True
            logger.info("✓ ReadMRZ engine available")
        except ImportError:
            engines['readmrz'] = False
            logger.warning("ReadMRZ not available")

        try:
            import passport_mrz_extractor
            engines['passport_mrz_extractor'] = True
            logger.info("✓ passport-mrz-extractor engine available")
        except ImportError:
            engines['passport_mrz_extractor'] = False
            logger.warning("passport-mrz-extractor not available")

        try:
            import pytesseract
            engines['tesseract'] = True
            logger.info("✓ Tesseract OCR available for direct extraction")
        except ImportError:
            engines['tesseract'] = False
            logger.warning("Tesseract not available")

        available_count = sum(engines.values())
        if available_count == 0:
            logger.error("No MRZ extraction engines available!")
        
        return engines

    def _detect_mrz_region(self, image):
        """Detect and crop MRZ region for better accuracy"""
        # For now, don't crop - let the libraries handle MRZ detection
        # They have better algorithms for finding MRZ zones
        return image

    def _preprocess_for_mrz(self, image, aggressive=False):
        """Advanced preprocessing specifically optimized for MRZ zones"""
        try:
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()

            # Resize if image is too small (MRZ needs good resolution)
            if gray.shape[0] < 100:
                scale = 200 / gray.shape[0]
                gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
                logger.info(f"Upscaled image for better OCR")

            if aggressive:
                # Aggressive preprocessing for difficult images
                
                # Strong denoising
                denoised = cv2.fastNlMeansDenoising(gray, h=20)
                
                # Enhance contrast dramatically
                clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4, 4))
                enhanced = clahe.apply(denoised)
                
                # Adaptive thresholding
                binary = cv2.adaptiveThreshold(
                    enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                    cv2.THRESH_BINARY, 15, 2
                )
                
                # Morphological operations to connect characters
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 1))
                processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
                
            else:
                # Moderate preprocessing for most images
                
                # Bilateral filter to reduce noise while preserving edges
                denoised = cv2.bilateralFilter(gray, 9, 75, 75)
                
                # Enhance contrast
                clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
                enhanced = clahe.apply(denoised)
                
                # Sharpen the image
                kernel_sharpen = np.array([[-1,-1,-1],
                                          [-1, 9,-1],
                                          [-1,-1,-1]])
                sharpened = cv2.filter2D(enhanced, -1, kernel_sharpen)
                
                # Slight thresholding
                _, processed = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            return processed

        except Exception as e:
            logger.warning(f"Advanced preprocessing failed: {e}, using basic grayscale")
            if len(image.shape) == 3:
                return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            return image

    def _create_preprocessing_variants(self, image) -> List[Tuple[str, np.ndarray]]:
        """Create multiple preprocessed variants for maximum compatibility"""
        variants = []
        
        # Work with full image - let MRZ libraries do their own region detection
        
        # Convert to grayscale once
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Variant 1: Original color (some libraries work better with color)
        variants.append(('original_color', image))
        
        # Variant 2: Original grayscale
        variants.append(('original_gray', gray))
        
        # Variant 3: Light enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        variants.append(('light_enhanced', enhanced))
        
        # Variant 4: Moderate preprocessing
        moderate = self._preprocess_for_mrz(image, aggressive=False)
        variants.append(('moderate', moderate))
        
        # Variant 5: Aggressive preprocessing
        aggressive = self._preprocess_for_mrz(image, aggressive=True)
        variants.append(('aggressive', aggressive))
        
        # Variant 6: High contrast binary (Otsu)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(('binary_otsu', binary))
        
        logger.info(f"Created {len(variants)} preprocessing variants")
        return variants

    def _normalize_extracted_data(self, data: Dict) -> Dict:
        """Normalize and return ALL extracted attributes from MRZ"""
        if not data:
            return {}
        
        # Create normalized output with ALL possible fields
        normalized = {}
        
        # Helper function to clean and normalize values
        def clean_value(value):
            if value is None:
                return ''
            value = str(value).strip()
            # Remove 'None', 'none', '<<<<' patterns
            value = value.replace('None', '').replace('none', '')
            value = re.sub(r'<+', '', value)
            return value.strip()
        
        # Personal information
        normalized['nom'] = clean_value(data.get('surname') or data.get('last_name') or data.get('nom'))
        normalized['prenom'] = clean_value(data.get('name') or data.get('given_names') or 
                                           data.get('given_name') or data.get('first_name') or data.get('prenom'))
        normalized['nom_complet'] = f"{normalized['prenom']} {normalized['nom']}".strip()
        
        # Sex/Gender
        normalized['sexe'] = clean_value(data.get('sex') or data.get('gender') or data.get('sexe'))
        
        # Nationality
        normalized['nationalite'] = clean_value(data.get('nationality') or data.get('issuing_country') or data.get('can'))
        
        # Document information
        normalized['type_document'] = clean_value(data.get('document_type') or data.get('type'))
        normalized['numero_document'] = clean_value(data.get('document_number') or data.get('document_no') or 
                                                     data.get('numero_carte') or data.get('passport_number'))
        normalized['numero_personnel'] = clean_value(data.get('personal_number') or data.get('optional_data') or 
                                                      data.get('optional_data_1') or data.get('optional_data_2'))
        
        # Dates - normalize to YYYYMMDD format
        birth_date = clean_value(data.get('birth_date') or data.get('date_of_birth') or data.get('date_naissance'))
        normalized['date_naissance'] = self._normalize_date(birth_date)
        
        expiry_date = clean_value(data.get('expiry_date') or data.get('expiration_date') or data.get('date_expiration'))
        normalized['date_expiration'] = self._normalize_date(expiry_date)
        
        issue_date = clean_value(data.get('issue_date') or data.get('date_emission'))
        normalized['date_emission'] = self._normalize_date(issue_date)
        
        # Additional fields that might be present
        normalized['lieu_naissance'] = clean_value(data.get('place_of_birth') or data.get('birth_place') or 
                                                    data.get('lieu_naissance'))
        normalized['pays_emission'] = clean_value(data.get('issuing_country') or data.get('pays_emission'))
        
        # Check digits and validation
        normalized['check_digit_document'] = clean_value(data.get('document_number_check_digit'))
        normalized['check_digit_naissance'] = clean_value(data.get('birth_date_check_digit'))
        normalized['check_digit_expiration'] = clean_value(data.get('expiry_date_check_digit'))
        normalized['check_digit_final'] = clean_value(data.get('final_check_digit') or data.get('composite_check_digit'))
        
        # Raw MRZ text for reference
        normalized['raw_mrz'] = clean_value(data.get('raw_text') or data.get('mrz_code') or 
                                            data.get('mrz_text') or data.get('raw_mrz'))
        
        # MRZ type/format
        normalized['mrz_type'] = clean_value(data.get('mrz_type') or data.get('document_format'))
        
        # Add any other fields that weren't mapped
        for key, value in data.items():
            normalized_key = key.lower().replace(' ', '_')
            if normalized_key not in normalized and clean_value(value):
                normalized[normalized_key] = clean_value(value)
                logger.info(f"Found additional field: {normalized_key} = {clean_value(value)}")
        
        # Remove empty fields
        normalized = {k: v for k, v in normalized.items() if v}
        
        logger.info(f"Normalized data contains {len(normalized)} non-empty fields")
        return normalized

    def _normalize_date(self, date_str: str) -> str:
        """Normalize date to YYYYMMDD format"""
        if not date_str:
            return ''
        
        # Remove separators
        date_str = date_str.replace('-', '').replace('/', '').replace('.', '').strip()
        
        # If already 8 digits (YYYYMMDD), return as-is
        if len(date_str) == 8 and date_str.isdigit():
            return date_str
        
        # If 6 digits (YYMMDD), convert to YYYYMMDD
        if len(date_str) == 6 and date_str.isdigit():
            year = date_str[:2]
            year_int = int(year)
            # Assume 00-50 is 2000-2050, 51-99 is 1951-1999
            century = '20' if year_int <= 50 else '19'
            return century + date_str
        
        return date_str

    def extract(self, image) -> Dict:
        """Extract MRZ data - comprehensive extraction with all attributes"""
        
        available_engines = [k for k, v in self.engines.items() if v]
        if not available_engines:
            logger.error("No MRZ engines available")
            return {}

        # Priority: passport_mrz_extractor, readmrz, then tesseract fallback
        engine_priority = ['passport_mrz_extractor', 'readmrz', 'tesseract']
        available_engines = [e for e in engine_priority if e in available_engines]
        
        # Create multiple preprocessed variants
        image_variants = self._create_preprocessing_variants(image)
        
        best_result = None
        max_fields = 0
        
        # Try each engine with each preprocessing variant
        for engine_name in available_engines:
            # For tesseract, only try if others failed
            if engine_name == 'tesseract' and max_fields > 0:
                continue
                
            for variant_name, processed_img in image_variants:
                logger.info(f"Trying {engine_name} with '{variant_name}' preprocessing")
                
                try:
                    if engine_name == 'passport_mrz_extractor':
                        result = self._extract_with_passport_mrz(processed_img)
                    elif engine_name == 'readmrz':
                        result = self._extract_with_readmrz(processed_img)
                    elif engine_name == 'tesseract':
                        result = self._extract_with_tesseract(processed_img)
                    else:
                        continue
                    
                    if result:
                        # Normalize the result to get all fields
                        normalized = self._normalize_extracted_data(result)
                        field_count = len([v for v in normalized.values() if v])
                        
                        logger.info(f"Extracted {field_count} fields with {engine_name} + {variant_name}")
                        
                        # Keep track of best result (most fields extracted)
                        if field_count > max_fields:
                            max_fields = field_count
                            best_result = normalized
                            logger.info(f"New best result: {field_count} fields")
                        
                        # If we got name AND document number, that's usually good enough
                        if normalized.get('nom') and normalized.get('numero_document'):
                            logger.info(f"✓ Complete MRZ extracted with {engine_name} + {variant_name}")
                            return normalized
                
                except Exception as e:
                    logger.warning(f"Extraction failed with {engine_name} + {variant_name}: {e}")
                    continue
        
        # Return best result found, even if incomplete
        if best_result and max_fields > 0:
            logger.info(f"✓ Returning best result with {max_fields} fields")
            return best_result
        
        logger.error("All MRZ extraction attempts failed")
        return {}

    def map_mrz_to_api_response(self, normalized_data: dict) -> dict:
        """
        Map normalized MRZ data to your API response structure.
        Returns ALL extracted fields in a structured format.
        """
        
        # Core identity fields
        response = {
            'prenom': normalized_data.get('prenom', ''),
            'nom': normalized_data.get('nom', ''),
            'nom_complet': normalized_data.get('nom_complet', ''),
            'sexe': normalized_data.get('sexe', ''),
            
            # Dates (already normalized to YYYYMMDD)
            'date_naissance': normalized_data.get('date_naissance', ''),
            'date_expiration': normalized_data.get('date_expiration', ''),
            'date_emission': normalized_data.get('date_emission', ''),
            'lieu_naissance': normalized_data.get('lieu_naissance', ''),
            
            # Document information
            'type_document': normalized_data.get('type_document', ''),
            'numero_carte': normalized_data.get('numero_document', ''),  # Map numero_document → numero_carte
            'numero_document': normalized_data.get('numero_document', ''),
            'numero_personnel': normalized_data.get('numero_personnel', ''),
            
            # Nationality and country
            'can': normalized_data.get('nationalite', ''),  # Map nationalite → can
            'nationalite': normalized_data.get('nationalite', ''),
            'pays_emission': normalized_data.get('pays_emission', ''),
            
            # Check digits (useful for validation)
            'check_digit_document': normalized_data.get('check_digit_document', ''),
            'check_digit_naissance': normalized_data.get('check_digit_naissance', ''),
            'check_digit_expiration': normalized_data.get('check_digit_expiration', ''),
            'check_digit_final': normalized_data.get('check_digit_final', ''),
            
            # Raw MRZ for reference/debugging
            'raw_mrz': normalized_data.get('raw_mrz', ''),
            'mrz_type': normalized_data.get('mrz_type', ''),
        }
        
        # Add any additional fields that were extracted but not in standard mapping
        additional_fields = {}
        standard_keys = set(response.keys()) | {
            'nom', 'prenom', 'nom_complet', 'sexe', 'date_naissance', 'date_expiration',
            'date_emission', 'lieu_naissance', 'type_document', 'numero_document',
            'numero_personnel', 'nationalite', 'pays_emission'
        }
        
        for key, value in normalized_data.items():
            if key not in standard_keys and value:
                additional_fields[key] = value
        
        if additional_fields:
            response['additional_fields'] = additional_fields
        
        # Remove empty fields for cleaner response
        response = {k: v for k, v in response.items() if v}
        
        return response

    def _extract_with_readmrz(self, image) -> Optional[Dict]:
        """Extract using ReadMRZ - returns raw data dict"""
        try:
            from readmrz import MrzDetector, MrzReader

            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp_path = tmp.name
                cv2.imwrite(tmp_path, image, [cv2.IMWRITE_PNG_COMPRESSION, 0])

            try:
                detector = MrzDetector()
                reader = MrzReader()

                mrz_image = detector.read(tmp_path)
                
                if mrz_image is None:
                    logger.debug("ReadMRZ: No MRZ region detected")
                    return None

                cropped = detector.crop_area(mrz_image)
                data = reader.process(cropped)
                
                if not data:
                    logger.debug("ReadMRZ: No data extracted")
                    return None

                logger.info(f"ReadMRZ: Extracted fields: {list(data.keys())}")
                return data  # Return raw data for normalization

            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        except Exception as e:
            logger.error(f"ReadMRZ extraction failed: {e}")
            return None

    def _extract_with_passport_mrz(self, image) -> Optional[Dict]:
        """Extract using passport-mrz-extractor - returns raw data dict"""
        try:
            import passport_mrz_extractor

            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp_path = tmp.name
                cv2.imwrite(tmp_path, image, [cv2.IMWRITE_PNG_COMPRESSION, 0])

            try:
                result = passport_mrz_extractor.read_mrz(tmp_path)
                
                if not result or not isinstance(result, dict):
                    logger.debug("passport-mrz-extractor: No data extracted")
                    return None
                
                logger.info(f"passport-mrz-extractor: Extracted fields: {list(result.keys())}")
                return result  # Return raw data for normalization

            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        except Exception as e:
            logger.error(f"passport-mrz-extractor extraction failed: {e}")
            return None

    def _extract_with_tesseract(self, image) -> Optional[Dict]:
        """Direct OCR extraction with Tesseract and manual MRZ parsing"""
        try:
            import pytesseract
            
            # Tesseract config optimized for MRZ (monospace font, limited charset)
            # MRZ uses: A-Z, 0-9, and < character
            custom_config = r'--psm 6 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<'
            
            # Extract text
            text = pytesseract.image_to_string(image, config=custom_config)
            
            if not text or len(text.strip()) < 30:
                logger.debug("Tesseract: Insufficient text extracted")
                return None
            
            logger.info(f"Tesseract: Extracted text ({len(text)} chars)")
            
            # Parse MRZ from extracted text
            result = self._parse_mrz_text(text)
            
            if result:
                logger.info(f"Tesseract: Successfully parsed MRZ data")
                return result
            
            logger.debug("Tesseract: Failed to parse MRZ from text")
            return None
            
        except Exception as e:
            logger.error(f"Tesseract extraction failed: {e}")
            return None

    def _parse_mrz_text(self, text: str) -> Optional[Dict]:
        """Parse MRZ format from raw text"""
        try:
            # Clean and split into lines
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            # Find lines that look like MRZ (contain << or are mostly uppercase with numbers)
            mrz_lines = []
            for line in lines:
                # MRZ lines are typically 30-44 characters, mostly uppercase, contain < or numbers
                if len(line) >= 28 and line.isupper() and ('<<' in line or any(c.isdigit() for c in line)):
                    mrz_lines.append(line)
            
            if len(mrz_lines) < 2:
                logger.debug(f"Not enough MRZ lines found: {len(mrz_lines)}")
                return None
            
            logger.info(f"Found {len(mrz_lines)} potential MRZ lines")
            
            # Try to parse based on MRZ format
            # TD1 (ID cards): 3 lines of 30 chars
            # TD2 (travel docs): 2 lines of 36 chars  
            # TD3 (passports): 2 lines of 44 chars
            
            if len(mrz_lines) >= 3 and len(mrz_lines[0]) == 30:
                # TD1 format (3 lines x 30 chars)
                return self._parse_td1_mrz(mrz_lines[:3])
            elif len(mrz_lines) >= 2:
                if len(mrz_lines[0]) >= 36 and len(mrz_lines[0]) <= 44:
                    # TD2 or TD3 format (2 lines)
                    return self._parse_td2_td3_mrz(mrz_lines[:2])
            
            logger.debug("MRZ format not recognized")
            return None
            
        except Exception as e:
            logger.error(f"MRZ parsing failed: {e}")
            return None

    def _parse_td1_mrz(self, lines: List[str]) -> Optional[Dict]:
        """Parse TD1 format (3 lines x 30 chars) - ID cards"""
        try:
            if len(lines) < 3:
                return None
            
            line1, line2, line3 = lines[0][:30], lines[1][:30], lines[2][:30]
            
            # Line 1: Document type (2) + Country (3) + Document number (9) + Check (1) + Optional (15)
            doc_type = line1[0:2].replace('<', '').strip()
            country = line1[2:5].replace('<', '').strip()
            doc_number = line1[5:14].replace('<', '').strip()
            
            # Line 2: Birth date (6) + Check (1) + Sex (1) + Expiry (6) + Check (1) + Nationality (3) + Optional (11) + Check (1)
            birth_date = line2[0:6]
            sex = line2[7:8]
            expiry_date = line2[8:14]
            nationality = line2[15:18].replace('<', '').strip()
            
            # Line 3: Name (30)
            name_field = line3.replace('<', ' ').strip()
            name_parts = [p.strip() for p in name_field.split('  ') if p.strip()]
            
            surname = name_parts[0] if name_parts else ''
            given_names = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
            
            return {
                'document_type': doc_type,
                'nationality': country or nationality,
                'document_number': doc_number,
                'birth_date': birth_date,
                'sex': sex,
                'expiry_date': expiry_date,
                'surname': surname,
                'name': given_names,
                'raw_text': '\n'.join(lines[:3])
            }
            
        except Exception as e:
            logger.error(f"TD1 parsing failed: {e}")
            return None

    def _parse_td2_td3_mrz(self, lines: List[str]) -> Optional[Dict]:
        """Parse TD2/TD3 format (2 lines) - Travel documents and passports"""
        try:
            if len(lines) < 2:
                return None
            
            line1, line2 = lines[0], lines[1]
            
            # Line 1: Type (1-2) + Country (3) + Name (remainder)
            doc_type = line1[0:2].replace('<', '').strip()
            country = line1[2:5].replace('<', '').strip()
            name_field = line1[5:].replace('<', ' ').strip()
            
            # Parse name (format: SURNAME<<GIVEN_NAMES)
            name_parts = [p.strip() for p in name_field.split('  ') if p.strip()]
            surname = name_parts[0] if name_parts else ''
            given_names = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
            
            # Line 2: Document number + Check + Nationality + Birth date + Check + Sex + Expiry + Check + Optional + Check
            doc_number_end = line2.find('<')
            if doc_number_end == -1:
                doc_number_end = 9
            
            doc_number = line2[0:doc_number_end].strip()
            
            # Find positions (varies by TD2/TD3)
            remaining = line2[doc_number_end:].replace('<', '')
            
            # Try to extract dates (YYMMDD format)
            date_pattern = re.findall(r'\d{6}', line2)
            birth_date = date_pattern[0] if len(date_pattern) > 0 else ''
            expiry_date = date_pattern[1] if len(date_pattern) > 1 else ''
            
            # Extract sex (M/F) - usually appears between dates
            sex_match = re.search(r'[MF]', line2[10:])
            sex = sex_match.group() if sex_match else ''
            
            # Nationality (3 chars after check digit)
            nationality = ''
            if len(line2) > 13:
                nat_candidate = line2[10:13].replace('<', '')
                if nat_candidate.isalpha():
                    nationality = nat_candidate
            
            if not nationality:
                nationality = country
            
            return {
                'document_type': doc_type,
                'nationality': nationality,
                'document_number': doc_number,
                'birth_date': birth_date,
                'sex': sex,
                'expiry_date': expiry_date,
                'surname': surname,
                'name': given_names,
                'raw_text': '\n'.join(lines[:2])
            }
            
        except Exception as e:
            logger.error(f"TD2/TD3 parsing failed: {e}")
            return None


# Example usage in your FastAPI endpoint:
def extract_text_endpoint(file):
    """Your existing endpoint - add this mapping"""
    
    # ... your existing code to get image and extract MRZ ...
    
    # Create MRZ extractor instance
    extractor = MRZExtractor()
    
    # ... your existing code to load/process the image ...
    # Assume you have 'image' loaded from the file
    
    # After getting normalized_data from extractor.extract(image):
    normalized_data = extractor.extract(image)
    
    if normalized_data:
        # Map to API response structure using the extractor instance
        structured_data = extractor.map_mrz_to_api_response(normalized_data)
        
        return {
            "success": True,
            "mrz_detected": True,
            "fields_extracted": len([v for v in normalized_data.values() if v]),
            "message": f"✅ MRZ detected - {len(normalized_data)} fields extracted",
            "structured_data": structured_data,
            "timestamp": datetime.now().isoformat(),
            "ocr_engines": extractor.engines
        }
    else:
        return {
            "success": False,
            "mrz_detected": False,
            "message": "❌ No MRZ data could be extracted",
            # ... rest of error response
        }