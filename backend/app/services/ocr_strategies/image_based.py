"""
Image-based OCR using PaddleOCR.

PaddleOCR is the sole OCR engine. It is lazily initialized on first use
so the application boots quickly even if model weights need downloading.
"""
import logging
import os
from pathlib import Path
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)


class PaddleOCREngine:
    """Singleton PaddleOCR wrapper with lazy initialization."""

    _instance = None
    _init_error: Optional[Exception] = None
    _initialized: bool = False

    @classmethod
    def _setup_environment(cls) -> Path:
        """Configure cache and temp directories for PaddleOCR on Windows."""
        cache_root = Path(__file__).resolve().parents[3] / ".paddle_cache"
        temp_root = cache_root / "tmp"
        cache_root.mkdir(parents=True, exist_ok=True)
        temp_root.mkdir(parents=True, exist_ok=True)

        drive = cache_root.drive or "C:"
        path_without_drive = str(cache_root)[len(drive):] or "\\"

        os.environ["HOME"] = str(cache_root)
        os.environ["USERPROFILE"] = str(cache_root)
        os.environ["HOMEDRIVE"] = drive
        os.environ["HOMEPATH"] = path_without_drive
        os.environ["TMP"] = str(temp_root)
        os.environ["TEMP"] = str(temp_root)
        os.environ["PADDLE_HOME"] = str(cache_root)
        os.environ["PADDLE_PDX_MODEL_HOME"] = str(cache_root)
        os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

        return cache_root

    @classmethod
    def get_instance(cls):
        """Return the PaddleOCR instance, creating it on first call."""
        if cls._instance is not None:
            return cls._instance

        if cls._init_error is not None:
            raise RuntimeError(
                f"PaddleOCR failed to initialize previously: {cls._init_error}"
            )

        try:
            cls._setup_environment()
            from paddleocr import PaddleOCR

            cls._instance = PaddleOCR(
                use_textline_orientation=False,  # disabled — medical PDFs are always upright, saves huge time per line
                lang="en",
                device="cpu",
                enable_hpi=False,
                enable_mkldnn=False,
            )
            cls._initialized = True
            logger.info("PaddleOCR engine initialized successfully")
            return cls._instance
        except Exception as exc:
            cls._init_error = exc
            logger.error(f"PaddleOCR initialization failed: {exc}")
            raise RuntimeError(f"PaddleOCR initialization failed: {exc}") from exc

    @classmethod
    def is_available(cls) -> bool:
        """Check whether PaddleOCR can be initialized."""
        if cls._instance is not None:
            return True
        if cls._init_error is not None:
            return False
        try:
            cls.get_instance()
            return True
        except Exception:
            return False

    @classmethod
    def extract_text(cls, image: Image.Image) -> str:
        """
        Extract text from a PIL Image using PaddleOCR.

        Args:
            image: PIL Image (any mode — will be converted to RGB).

        Returns:
            Extracted text as a single string with lines joined by newlines.

        Raises:
            RuntimeError: If PaddleOCR is not available.
            ValueError: If extraction produces no usable text.
        """
        import numpy as np

        ocr = cls.get_instance()
        image_array = np.array(image.convert("RGB"))

        # PaddleOCR >=2.8 exposes `predict`, older versions use `ocr`.
        if hasattr(ocr, "predict"):
            result = ocr.predict(image_array)
        elif hasattr(ocr, "ocr"):
            result = ocr.ocr(image_array, cls=True)
        else:
            raise RuntimeError(
                "PaddleOCR instance has no supported inference method (predict/ocr)"
            )

        if not result:
            return ""

        text_lines: list[str] = []
        for block in result:
            if not block:
                continue

            # Newer pipeline: block has a `rec_texts` attribute or dict key
            if hasattr(block, "rec_texts"):
                text_lines.extend(
                    t.strip() for t in block.rec_texts if t and t.strip()
                )
                continue
            if isinstance(block, dict) and "rec_texts" in block:
                text_lines.extend(
                    t.strip() for t in block["rec_texts"] if t and t.strip()
                )
                continue

            # Legacy format: list of [box, (text, confidence)] per line
            for line in block:
                if not line or len(line) < 2:
                    continue
                text = line[1][0] if line[1] else ""
                if text and text.strip():
                    text_lines.append(text.strip())

        return "\n".join(text_lines).strip()
