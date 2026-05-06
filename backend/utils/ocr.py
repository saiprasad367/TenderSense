"""
OCR Pipeline — PaddleOCR primary, Tesseract fallback, IndicBERT hint for Kannada.
Returns structured text blocks with page numbers and confidence.
"""
from __future__ import annotations

import asyncio
import io
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("tendersense.ocr")


class OCRResult:
    def __init__(self, text: str, confidence: float, page: int, blocks: list):
        self.text = text
        self.confidence = confidence
        self.page = page
        self.blocks = blocks   # [{text, bbox, confidence}]


class OCRPipeline:
    """
    Multi-engine OCR pipeline.
    1. Try PaddleOCR (best for mixed English/Kannada tables & stamps)
    2. Fallback to pytesseract if PaddleOCR unavailable
    """

    def __init__(self):
        self._paddle_en = None
        self._paddle_ka = None
        self._paddle_en_loaded = False
        self._paddle_ka_loaded = False

    def _load_paddle(self, lang: str = "en"):
        if lang == "en" and self._paddle_en_loaded:
            return
        if lang == "ka" and self._paddle_ka_loaded:
            return
            
        try:
            from paddleocr import PaddleOCR
            if lang == "en":
                self._paddle_en = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
                self._paddle_en_loaded = True
            else:
                self._paddle_ka = PaddleOCR(use_angle_cls=True, lang="ka", show_log=False)
                self._paddle_ka_loaded = True
            logger.info(f"PaddleOCR initialized for lang={lang}")
        except ImportError:
            logger.warning("PaddleOCR not installed — will use Tesseract fallback")

    async def extract_from_pdf(self, pdf_bytes: bytes) -> List[OCRResult]:
        """Extract text from all pages of a PDF, returning per-page OCRResult list."""
        return await asyncio.get_event_loop().run_in_executor(
            None, self._sync_extract_pdf, pdf_bytes
        )

    def _sync_extract_pdf(self, pdf_bytes: bytes) -> List[OCRResult]:
        results: List[OCRResult] = []
        lang = "en"
        
        try:
            import fitz  # pymupdf
        except ImportError:
            logger.error("pymupdf not installed — cannot split PDF pages")
            return results

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        for page_num, page in enumerate(doc, start=1):
            # Render page to image at 200 DPI
            mat = fitz.Matrix(200 / 72, 200 / 72)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")

            # Try text layer first (for digital PDFs — fast path)
            native_text = page.get_text("text").strip()
            if page_num == 1 and len(native_text) > 50:
                try:
                    from langdetect import detect
                    if detect(native_text[:200]) == 'kn':  # langdetect uses 'kn' for Kannada
                        lang = "ka"  # PaddleOCR uses 'ka'
                except Exception:
                    pass

            self._load_paddle(lang)
            
            if len(native_text) > 50:
                results.append(OCRResult(
                    text=native_text,
                    confidence=1.0,
                    page=page_num,
                    blocks=[],
                ))
                continue

            # OCR path for scanned pages
            ocr_result = self._ocr_image(img_bytes, page_num, lang)
            results.append(ocr_result)

        doc.close()
        return results

    def _ocr_image(self, img_bytes: bytes, page_num: int, lang: str = "en") -> OCRResult:
        paddle_inst = self._paddle_en if lang == "en" else self._paddle_ka
        
        # PaddleOCR path
        if paddle_inst is not None:
            try:
                import numpy as np
                from PIL import Image

                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                img_np = np.array(img)
                paddle_result = paddle_inst.ocr(img_np, cls=True)

                lines: List[str] = []
                blocks: List[dict] = []
                confidences: List[float] = []

                if paddle_result and paddle_result[0]:
                    for line in paddle_result[0]:
                        bbox, (text, conf) = line
                        lines.append(text)
                        confidences.append(conf)
                        blocks.append({"text": text, "bbox": bbox, "confidence": conf})

                avg_conf = float(sum(confidences) / len(confidences)) if confidences else 0.0
                return OCRResult(
                    text="\n".join(lines),
                    confidence=avg_conf,
                    page=page_num,
                    blocks=blocks,
                )
            except Exception as exc:
                logger.warning(f"PaddleOCR page {page_num} failed: {exc} — falling back to Tesseract")

        # Tesseract fallback
        return self._tesseract_image(img_bytes, page_num)

    def _tesseract_image(self, img_bytes: bytes, page_num: int) -> OCRResult:
        try:
            import pytesseract
            from PIL import Image

            img = Image.open(io.BytesIO(img_bytes))
            data = pytesseract.image_to_data(
                img,
                lang="eng+kan",  # English + Kannada
                output_type=pytesseract.Output.DICT,
            )
            words = [
                w for w, c in zip(data["text"], data["conf"])
                if w.strip() and int(c) > 30
            ]
            confs = [int(c) for c in data["conf"] if int(c) > 0]
            avg_conf = (sum(confs) / len(confs) / 100) if confs else 0.0

            return OCRResult(
                text=" ".join(words),
                confidence=avg_conf,
                page=page_num,
                blocks=[],
            )
        except Exception as exc:
            logger.error(f"Tesseract page {page_num} failed: {exc}")
            return OCRResult(text="", confidence=0.0, page=page_num, blocks=[])

    def full_text(self, results: List[OCRResult]) -> str:
        """Concatenate all pages into single string."""
        return "\n\n".join(
            f"[PAGE {r.page}]\n{r.text}" for r in results if r.text
        )


# Singleton
_pipeline: Optional[OCRPipeline] = None


def get_ocr_pipeline() -> OCRPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = OCRPipeline()
    return _pipeline
