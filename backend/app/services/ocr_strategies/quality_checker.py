"""
Text quality validation for OCR results
"""
import re
import logging

logger = logging.getLogger(__name__)

class TextQualityChecker:
    """Validate extracted text quality"""
    
    @staticmethod
    def is_good_quality(text: str, min_length: int = 100) -> bool:
        """
        Check if extracted text is good quality.
        
        Criteria:
        - Minimum length
        - High alphanumeric ratio
        - Not too many special characters
        - Contains medical keywords
        
        Args:
            text: Extracted text to validate
            min_length: Minimum acceptable text length
            
        Returns:
            True if text is good quality
        """
        if not text or len(text) < min_length:
            logger.warning(f"Text too short: {len(text) if text else 0} chars")
            return False
        
        # Calculate alphanumeric ratio
        alphanum_count = sum(c.isalnum() or c.isspace() for c in text)
        alphanum_ratio = alphanum_count / len(text)
        
        # Should be mostly readable characters
        if alphanum_ratio < 0.70:
            logger.warning(f"Low alphanumeric ratio: {alphanum_ratio:.2f}")
            return False
        
        # Check for medical keywords (indicates proper extraction)
        medical_keywords = [
            'patient', 'test', 'result', 'report', 'laboratory',
            'diagnosis', 'specimen', 'date', 'name', 'age', 'doctor',
            'clinical', 'medical', 'hospital', 'examination'
        ]
        
        text_lower = text.lower()
        keyword_matches = sum(1 for kw in medical_keywords if kw in text_lower)
        
        if keyword_matches < 2:
            logger.warning(f"Few medical keywords found: {keyword_matches}")
            # Don't fail immediately - might still be valid
        
        logger.info(f"Text quality: GOOD (ratio={alphanum_ratio:.2f}, keywords={keyword_matches})")
        return True
    
    @staticmethod
    def get_quality_score(text: str) -> float:
        """
        Get quality score 0-100.
        
        Args:
            text: Text to score
            
        Returns:
            Quality score (0-100)
        """
        if not text:
            return 0.0
        
        score = 0.0
        
        # Length score (max 20 points)
        if len(text) > 100:
            score += min(20, len(text) / 100)
        
        # Alphanumeric ratio (max 40 points)
        alphanum_ratio = sum(c.isalnum() or c.isspace() for c in text) / len(text)
        score += alphanum_ratio * 40
        
        # Medical keywords (max 40 points)
        medical_keywords = [
            'patient', 'test', 'result', 'report', 'laboratory',
            'diagnosis', 'specimen', 'date', 'name', 'age', 'doctor',
            'clinical', 'medical', 'hospital', 'examination', 'treatment'
        ]
        
        text_lower = text.lower()
        keyword_count = sum(1 for kw in medical_keywords if kw in text_lower)
        score += min(40, keyword_count * 3)
        
        return min(100.0, score)
    
    @staticmethod
    def diagnose_issues(text: str) -> dict:
        """
        Diagnose quality issues with extracted text.
        
        Returns:
            Dictionary with issue analysis
        """
        if not text:
            return {"error": "No text provided"}
        
        issues = []
        metrics = {}
        
        # Length check
        metrics['length'] = len(text)
        if len(text) < 100:
            issues.append(f"Text too short ({len(text)} chars)")
        
        # Character distribution
        alphanum_count = sum(c.isalnum() for c in text)
        space_count = sum(c.isspace() for c in text)
        special_count = len(text) - alphanum_count - space_count
        
        metrics['alphanum_ratio'] = alphanum_count / len(text) if len(text) > 0 else 0
        metrics['space_ratio'] = space_count / len(text) if len(text) > 0 else 0
        metrics['special_ratio'] = special_count / len(text) if len(text) > 0 else 0
        
        if metrics['alphanum_ratio'] < 0.7:
            issues.append(f"Low alphanumeric ratio ({metrics['alphanum_ratio']:.2%})")
        
        if metrics['special_ratio'] > 0.2:
            issues.append(f"Too many special characters ({metrics['special_ratio']:.2%})")
        
        # Medical keywords
        medical_keywords = ['patient', 'test', 'result', 'report', 'laboratory']
        text_lower = text.lower()
        keyword_matches = [kw for kw in medical_keywords if kw in text_lower]
        metrics['medical_keywords'] = len(keyword_matches)
        
        if len(keyword_matches) < 2:
            issues.append(f"Few medical keywords ({len(keyword_matches)} found)")
        
        return {
            'quality_score': TextQualityChecker.get_quality_score(text),
            'metrics': metrics,
            'issues': issues,
            'is_good': len(issues) == 0
        }
