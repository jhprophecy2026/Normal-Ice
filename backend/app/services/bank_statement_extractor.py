"""
Gemini extractor for bank payment confirmation / bank statement.
Extracts UTR, amount, date, bank details, transaction type from any
standard Indian bank NEFT/RTGS/IMPS/UPI confirmation document.
"""
import json
import logging
from typing import List
from PIL import Image

from app.models.bank_statement import BankStatementExtract
from app.services.llm import GeminiExtractor

logger = logging.getLogger(__name__)

_PROMPT = """You are a financial data extraction assistant for a hospital TPA settlement system.

Extract ONLY the following fields from the bank payment confirmation / bank statement text below.
This could be a NEFT / RTGS / IMPS / UPI payment confirmation, bank-generated PDF advice, or transaction receipt.

Document Text:
{text}

Return ONLY this JSON object (use null for any field not found):
{{
  "utr_number":       "string or null — UTR / transaction reference / RRN number",
  "amount":           "number or null — transferred amount in INR (plain number, no symbols or commas)",
  "transaction_date": "YYYY-MM-DD or null — date of transfer",
  "transaction_type": "string or null — one of: NEFT, RTGS, IMPS, UPI, CHEQUE, or as stated",
  "sender_bank":      "string or null — paying bank name",
  "sender_account":   "string or null — payer account number (mask middle digits if shown, e.g. XXXX1234)",
  "receiver_bank":    "string or null — beneficiary bank name",
  "receiver_account": "string or null — beneficiary account number (masked)",
  "ifsc_code":        "string or null — IFSC code of receiving branch",
  "narration":        "string or null — transaction narration / remarks / purpose"
}}

Rules:
- Return ONLY the JSON, no markdown fences, no extra text
- All monetary values must be plain numbers without currency symbols or commas
- Dates must be in YYYY-MM-DD format
"""

_MULTIMODAL_PROMPT = """You are a financial data extraction assistant for a hospital TPA settlement system.

You will receive OCR text AND page images of a bank payment confirmation.
Use images as the primary source when OCR text is incomplete or noisy.

OCR Text:
{text}

Return ONLY this JSON object (use null for any field not found):
{{
  "utr_number":       "string or null",
  "amount":           "number or null",
  "transaction_date": "YYYY-MM-DD or null",
  "transaction_type": "string or null",
  "sender_bank":      "string or null",
  "sender_account":   "string or null",
  "receiver_bank":    "string or null",
  "receiver_account": "string or null",
  "ifsc_code":        "string or null",
  "narration":        "string or null"
}}

Rules:
- Return ONLY the JSON, no markdown, no explanation
- Monetary values: plain numbers only
- Dates: YYYY-MM-DD
"""


def extract_bank_statement(text: str, images: List[Image.Image] | None = None) -> BankStatementExtract:
    extractor = GeminiExtractor()
    try:
        if images:
            prompt = _MULTIMODAL_PROMPT.format(text=text[:6000])
            raw = extractor.extract_with_images(prompt, images)
        else:
            prompt = _PROMPT.format(text=text[:6000])
            raw = extractor.extract(prompt)

        data = json.loads(raw)
        return BankStatementExtract(**{k: v for k, v in data.items() if k in BankStatementExtract.model_fields})
    except Exception as e:
        logger.error(f"Bank statement extraction failed: {e}")
        return BankStatementExtract()
