"""
Formal HTML email templates for each TPA communication step.
All templates follow a consistent professional design matching
Indian TPA communication standards.
"""
from datetime import datetime


def _inr(val) -> str:
    if val is None:
        return "—"
    try:
        return f"&#8377;{float(val):,.0f}"
    except Exception:
        return str(val)


def _date(val) -> str:
    if not val:
        return "—"
    return str(val)[:10]


def _now() -> str:
    return datetime.now().strftime("%d %b %Y, %I:%M %p")


# ---------------------------------------------------------------------------
# Shared layout helpers
# ---------------------------------------------------------------------------

def _header(badge_label: str, badge_color: str = "#1e3a5f") -> str:
    return f"""
    <tr>
      <td style="background:#1e3a5f;padding:24px 36px;">
        <p style="color:#ffffff;font-size:18px;font-weight:bold;margin:0;letter-spacing:-0.3px;">
          ClinicalFHIR
        </p>
        <p style="color:#94a3b8;font-size:11px;margin:3px 0 0;letter-spacing:0.2px;">
          Healthcare RCM Platform — TPA Communication
        </p>
      </td>
    </tr>
    <tr>
      <td style="background:#f1f5f9;padding:12px 36px;border-bottom:1px solid #e2e8f0;">
        <span style="background:{badge_color};color:#fff;font-size:10px;font-weight:bold;
                     padding:4px 12px;border-radius:20px;text-transform:uppercase;letter-spacing:0.8px;">
          {badge_label}
        </span>
      </td>
    </tr>
"""


def _footer(hospital_name: str = "") -> str:
    return f"""
    <tr>
      <td style="background:#f8fafc;padding:16px 36px;border-top:1px solid #e2e8f0;">
        <p style="color:#94a3b8;font-size:11px;margin:0;line-height:1.6;">
          This is a system-generated communication from
          <strong>{hospital_name or "the hospital"}</strong>'s TPA Management System.<br>
          Please do not reply to this email directly — contact the hospital TPA desk for queries.<br>
          Generated on {_now()}
        </p>
      </td>
    </tr>
"""


def _ref_box(bill_no: str, patient_name: str) -> str:
    return f"""
    <table width="100%" cellpadding="0" cellspacing="0"
           style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;margin:0 0 24px;">
      <tr>
        <td style="padding:12px 16px;">
          <p style="color:#3b82f6;font-size:10px;font-weight:bold;text-transform:uppercase;
                    letter-spacing:0.8px;margin:0 0 4px;">Case Reference</p>
          <p style="color:#1e3a5f;font-size:15px;font-weight:bold;margin:0;">
            {bill_no} &nbsp;&bull;&nbsp; {patient_name or "—"}
          </p>
        </td>
      </tr>
    </table>
"""


def _section(title: str, rows: list[tuple[str, str]]) -> str:
    row_html = ""
    for i, (label, value) in enumerate(rows):
        bg = "#f8fafc" if i % 2 == 0 else "#ffffff"
        row_html += f"""
        <tr style="background:{bg};">
          <td style="padding:9px 14px;color:#64748b;font-size:12px;width:42%;border-right:1px solid #e2e8f0;">
            {label}
          </td>
          <td style="padding:9px 14px;color:#1e293b;font-size:12px;font-weight:600;">
            {value or "—"}
          </td>
        </tr>"""
    return f"""
    <p style="color:#1e3a5f;font-size:11px;font-weight:bold;text-transform:uppercase;
              letter-spacing:0.8px;margin:0 0 8px;">{title}</p>
    <table width="100%" cellpadding="0" cellspacing="0"
           style="border:1px solid #e2e8f0;border-radius:6px;overflow:hidden;margin:0 0 20px;">
      {row_html}
    </table>
"""


def _wrap(body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:Arial,Helvetica,sans-serif;-webkit-font-smoothing:antialiased;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:32px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:10px;overflow:hidden;
                    border:1px solid #e2e8f0;box-shadow:0 2px 8px rgba(0,0,0,.06);">
        {body}
      </table>
    </td></tr>
  </table>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Template 1 — Pre-Authorization Request
# ---------------------------------------------------------------------------

def preauth_email(pa: dict) -> tuple[str, str]:
    """Returns (subject, html)."""
    tpa   = pa.get("tpa_name") or pa.get("insurance_company") or "TPA"
    hosp  = pa.get("hospital_name") or "the hospital"
    pt    = pa.get("patient_name") or "Patient"
    bill  = pa.get("bill_no") or "—"

    subject = f"Pre-Authorization Request | {pt} | {bill} | {hosp}"

    body = _header("Pre-Authorization Request", "#1e3a5f")
    body += f"""
    <tr><td style="padding:32px 36px 24px;">
      <p style="color:#1e293b;font-size:14px;margin:0 0 6px;">To,</p>
      <p style="color:#1e293b;font-size:14px;font-weight:bold;margin:0 0 20px;">
        Claims &amp; Authorization Department<br>
        <span style="color:#3b82f6;">{tpa}</span>
      </p>
      <p style="color:#475569;font-size:13px;line-height:1.7;margin:0 0 24px;">
        We hereby submit a <strong>Pre-Authorization Request</strong> for cashless hospitalization
        on behalf of the insured patient detailed below. Kindly review the enclosed information
        and provide authorization at the earliest.
      </p>

      {_ref_box(bill, pt)}

      {_section("Patient &amp; Policy Details", [
          ("Patient Name",       pa.get("patient_name")),
          ("ABHA ID",            pa.get("abha_id")),
          ("Date of Birth",      _date(pa.get("date_of_birth"))),
          ("Gender",             pa.get("gender")),
          ("Policy No.",         pa.get("policy_no")),
          ("Insurance Company",  pa.get("insurance_company")),
          ("TPA",                pa.get("tpa_name")),
          ("Insured Card ID",    pa.get("insured_card_id")),
      ])}

      {_section("Admission Details", [
          ("Hospital",           pa.get("hospital_name")),
          ("ROHINI ID",          pa.get("rohini_id")),
          ("Attending Physician",pa.get("doctor_name")),
          ("Admission Date",     _date(pa.get("admission_date"))),
          ("Admission Type",     pa.get("admission_type")),
          ("Room Type",          pa.get("room_type")),
          ("Expected Duration",  f"{pa.get('expected_days_in_hospital', '—')} days"),
      ])}

      {_section("Clinical Information", [
          ("Provisional Diagnosis", pa.get("provisional_diagnosis")),
          ("ICD-10 Code",           pa.get("icd10_diagnosis_code")),
          ("Presenting Complaints", pa.get("presenting_complaints")),
          ("Treatment Type",        "Surgical" if pa.get("treatment_surgical") else "Medical"),
          ("Surgery / Procedure",   pa.get("surgery_name")),
          ("ICD-10 PCS Code",       pa.get("icd10_pcs_code")),
      ])}

      {_section("Estimated Cost Breakdown", [
          ("Room Rent / Day",        _inr(pa.get("room_rent_per_day"))),
          ("ICU Charges / Day",      _inr(pa.get("icu_charges_per_day"))),
          ("OT / Surgery Charges",   _inr(pa.get("ot_charges"))),
          ("Surgeon Fees",           _inr(pa.get("surgeon_fees"))),
          ("Medicines &amp; Consumables", _inr(pa.get("medicines_consumables"))),
          ("Investigations",         _inr(pa.get("investigations"))),
          ("Total Estimated Cost",   _inr(pa.get("total_estimated_cost"))),
      ])}

      <p style="color:#475569;font-size:13px;line-height:1.7;margin:24px 0 0;">
        A Pre-Authorization Form (PDF) has been generated and is available on the hospital
        TPA portal. Kindly process this request and communicate the authorization status
        to the hospital TPA desk at the earliest.
      </p>
    </td></tr>
    """
    body += _footer(hosp)

    return subject, _wrap(body)


# ---------------------------------------------------------------------------
# Template 2 — Enhancement Request
# ---------------------------------------------------------------------------

def enhancement_email(enh: dict, pa: dict) -> tuple[str, str]:
    tpa   = pa.get("tpa_name") or pa.get("insurance_company") or "TPA"
    hosp  = pa.get("hospital_name") or "the hospital"
    pt    = pa.get("patient_name") or "Patient"
    bill  = pa.get("bill_no") or enh.get("bill_no") or "—"
    seq   = enh.get("sequence_no") or 1

    subject = f"Enhancement Request No. {seq} | {pt} | {bill} | {hosp}"

    orig_cost    = _inr(enh.get("original_total_cost"))
    revised_cost = _inr(enh.get("revised_total_estimated_cost"))
    try:
        orig_v    = float(enh.get("original_total_cost") or 0)
        revised_v = float(enh.get("revised_total_estimated_cost") or 0)
        diff      = revised_v - orig_v
        diff_str  = f"&#8377;{abs(diff):,.0f} ({'increase' if diff > 0 else 'decrease'})"
    except Exception:
        diff_str  = "—"

    body = _header(f"Enhancement Request No. {seq}", "#7c3aed")
    body += f"""
    <tr><td style="padding:32px 36px 24px;">
      <p style="color:#1e293b;font-size:14px;margin:0 0 6px;">To,</p>
      <p style="color:#1e293b;font-size:14px;font-weight:bold;margin:0 0 20px;">
        Claims &amp; Authorization Department<br>
        <span style="color:#7c3aed;">{tpa}</span>
      </p>
      <p style="color:#475569;font-size:13px;line-height:1.7;margin:0 0 24px;">
        This is to inform you of a <strong>revision to the pre-authorized treatment plan</strong>
        for the patient mentioned below. We request a corresponding enhancement to the
        pre-authorization amount.
      </p>

      {_ref_box(bill, pt)}

      {_section("Enhancement Details", [
          ("Enhancement Sequence No.", str(seq)),
          ("Reason for Enhancement",   enh.get("reason")),
          ("Clinical Justification",   enh.get("clinical_justification")),
      ])}

      {_section("Updated Clinical Information", [
          ("Original Diagnosis",  enh.get("original_diagnosis") or pa.get("provisional_diagnosis")),
          ("Updated Diagnosis",   enh.get("updated_diagnosis")),
          ("Original ICD-10",     enh.get("original_icd10_code") or pa.get("icd10_diagnosis_code")),
          ("Updated ICD-10",      enh.get("updated_icd10_code")),
          ("Updated Surgery",     enh.get("updated_surgery_name")),
          ("Updated ICD-10 PCS",  enh.get("updated_icd10_pcs_code")),
          ("Line of Treatment",   enh.get("updated_line_of_treatment")),
      ])}

      {_section("Revised Cost Estimate", [
          ("Original Approved Amount",  orig_cost),
          ("Revised Total Estimate",    revised_cost),
          ("Enhancement (Difference)",  diff_str),
          ("Room Rent / Day",           _inr(enh.get("revised_room_rent_per_day"))),
          ("ICU Charges / Day",         _inr(enh.get("revised_icu_charges_per_day"))),
          ("OT / Surgery",              _inr(enh.get("revised_ot_charges"))),
          ("Surgeon Fees",              _inr(enh.get("revised_surgeon_fees"))),
          ("Medicines &amp; Consumables", _inr(enh.get("revised_medicines_consumables"))),
          ("Investigations",            _inr(enh.get("revised_investigations"))),
      ])}

      <p style="color:#475569;font-size:13px;line-height:1.7;margin:24px 0 0;">
        Kindly approve the enhanced amount at the earliest to ensure uninterrupted
        cashless treatment for the patient.
      </p>
    </td></tr>
    """
    body += _footer(hosp)

    return subject, _wrap(body)


# ---------------------------------------------------------------------------
# Template 3 — Discharge Intimation
# ---------------------------------------------------------------------------

def discharge_email(dis: dict, pa: dict) -> tuple[str, str]:
    tpa  = pa.get("tpa_name") or pa.get("insurance_company") or "TPA"
    hosp = pa.get("hospital_name") or "the hospital"
    pt   = pa.get("patient_name") or "Patient"
    bill = dis.get("bill_no") or pa.get("bill_no") or "—"

    subject = f"Discharge Intimation &amp; Final Bill Submission | {pt} | {bill} | {hosp}"

    body = _header("Discharge Intimation", "#059669")
    body += f"""
    <tr><td style="padding:32px 36px 24px;">
      <p style="color:#1e293b;font-size:14px;margin:0 0 6px;">To,</p>
      <p style="color:#1e293b;font-size:14px;font-weight:bold;margin:0 0 20px;">
        Claims &amp; Settlement Department<br>
        <span style="color:#059669;">{tpa}</span>
      </p>
      <p style="color:#475569;font-size:13px;line-height:1.7;margin:0 0 24px;">
        We hereby submit the <strong>Discharge Intimation and Final Hospital Bill</strong>
        for the above-referenced case. The patient has been discharged and the final
        bill is ready for TPA processing and settlement.
      </p>

      {_ref_box(bill, pt)}

      {_section("Discharge Summary", [
          ("Patient Name",         pa.get("patient_name")),
          ("ABHA ID",              pa.get("abha_id")),
          ("Policy No.",           pa.get("policy_no")),
          ("Hospital",             pa.get("hospital_name")),
          ("Admission Date",       _date(pa.get("admission_date"))),
          ("Discharge Date",       _date(dis.get("discharge_date"))),
          ("Final Diagnosis",      dis.get("final_diagnosis") or pa.get("provisional_diagnosis")),
          ("ICD-10 (Final)",       dis.get("final_icd10_codes") or pa.get("icd10_diagnosis_code")),
          ("Procedure Codes",      dis.get("procedure_codes")),
      ])}

      {_section("Final Bill Breakdown", [
          ("Room Charges",          _inr(dis.get("room_charges"))),
          ("ICU Charges",           _inr(dis.get("icu_charges"))),
          ("Surgery / OT Charges",  _inr(dis.get("surgery_charges"))),
          ("Medicines &amp; Consumables", _inr(dis.get("medicine_charges"))),
          ("Investigations",        _inr(dis.get("investigation_charges"))),
          ("Other Charges",         _inr(dis.get("other_charges"))),
          ("Pre-Auth Estimate",     _inr(pa.get("total_estimated_cost"))),
          ("Total Final Bill",      _inr(dis.get("total_bill_amount"))),
      ])}

      <p style="color:#475569;font-size:13px;line-height:1.7;margin:24px 0 0;">
        Kindly process the final claim settlement at the earliest. All supporting
        documents including discharge summary, investigation reports, and original
        bills are available at the hospital TPA desk.
      </p>
    </td></tr>
    """
    body += _footer(hosp)

    return subject, _wrap(body)


# ---------------------------------------------------------------------------
# Template 4 — Settlement Confirmation
# ---------------------------------------------------------------------------

def settlement_email(sett: dict, pa: dict, dis: dict | None) -> tuple[str, str]:
    tpa    = pa.get("tpa_name") or pa.get("insurance_company") or "TPA"
    hosp   = pa.get("hospital_name") or "the hospital"
    pt     = pa.get("patient_name") or "Patient"
    bill   = sett.get("bill_no") or pa.get("bill_no") or "—"
    status = (sett.get("status") or "pending").upper()

    subject = f"Settlement {status} — Acknowledgment | {pt} | {bill} | {hosp}"

    status_color = {"APPROVED": "#16a34a", "PAID": "#7c3aed", "REJECTED": "#dc2626"}.get(status, "#64748b")

    body = _header(f"Settlement {status}", status_color)
    body += f"""
    <tr><td style="padding:32px 36px 24px;">
      <p style="color:#1e293b;font-size:14px;margin:0 0 6px;">To,</p>
      <p style="color:#1e293b;font-size:14px;font-weight:bold;margin:0 0 20px;">
        Claims &amp; Settlement Department<br>
        <span style="color:{status_color};">{tpa}</span>
      </p>
      <p style="color:#475569;font-size:13px;line-height:1.7;margin:0 0 24px;">
        This communication serves as an <strong>acknowledgment of the settlement decision</strong>
        for the case referenced below. Please find the settlement summary attached.
      </p>

      {_ref_box(bill, pt)}

      {_section("Settlement Summary", [
          ("Patient Name",           pa.get("patient_name")),
          ("ABHA ID",                pa.get("abha_id")),
          ("Policy No.",             pa.get("policy_no")),
          ("Hospital",               pa.get("hospital_name")),
          ("Discharge Date",         _date(dis.get("discharge_date") if dis else None)),
          ("Settlement Date",        _date(sett.get("settlement_date"))),
          ("Settlement Status",      status),
      ])}

      {_section("Financial Summary", [
          ("Pre-Auth Approved Amount",  _inr(sett.get("pre_auth_approved_amount") or pa.get("total_estimated_cost"))),
          ("Final Claimed Amount",      _inr(sett.get("claimed_amount") or (dis.get("total_bill_amount") if dis else None))),
          ("Deduction Amount",          _inr(sett.get("deduction_amount"))),
          ("Deduction Reason",          sett.get("deduction_reason")),
          ("Final Settlement Amount",   _inr(sett.get("final_settlement_amount"))),
          ("TPA Remarks",               sett.get("tpa_remarks")),
      ])}

      <p style="color:#475569;font-size:13px;line-height:1.7;margin:24px 0 0;">
        {"The settlement has been approved and processed. Please initiate the payment transfer to the hospital account at the earliest." if status == "APPROVED"
         else "Payment has been released. Kindly confirm receipt and update your records accordingly." if status == "PAID"
         else "The claim has been processed. Please contact the TPA desk for further information regarding this decision."}
      </p>
    </td></tr>
    """
    body += _footer(hosp)

    return subject, _wrap(body)
