from typing import Optional
from pydantic import BaseModel


class BankStatementExtract(BaseModel):
    utr_number:       Optional[str]   = None
    amount:           Optional[float] = None
    transaction_date: Optional[str]   = None
    transaction_type: Optional[str]   = None   # NEFT / RTGS / IMPS / UPI
    sender_bank:      Optional[str]   = None
    sender_account:   Optional[str]   = None
    receiver_bank:    Optional[str]   = None
    receiver_account: Optional[str]   = None
    ifsc_code:        Optional[str]   = None
    narration:        Optional[str]   = None


class BankStatementResponse(BankStatementExtract):
    id:            str
    bill_no:       str
    settlement_id: Optional[str] = None
    created_at:    Optional[str] = None
