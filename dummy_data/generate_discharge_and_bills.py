"""
Discharge Summary + Final Bill PDF Generator
=============================================
Generates 10 discharge summary PDFs + 10 final hospital bill PDFs.

Patients covered:
  Group A — Original 5 ABHA registry patients (Rahul Sharma, Priya Menon,
             Arun Patel, Sunita Rao, Vikram Singh)
  Group B — New 5 case patients from generate_new_cases.py (Ramesh Sharma,
             Sunita Agarwal, Vikram Chauhan, Kavita Mishra, Anjali Reddy)

Each discharge summary is deliberately crafted to test the system's
"missing data" detection — some documents omit ICD-10 codes, procedure codes,
cost breakdowns, or key identifiers to simulate real-world incomplete submissions.

Output:
  dummy_data/discharge_summaries/*.pdf   (10 files)
  dummy_data/final_bills/*.pdf           (10 files)

Run:
  backend\\venv\\Scripts\\python.exe dummy_data\\generate_discharge_and_bills.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from fpdf import FPDF, XPos, YPos
from datetime import date

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
DARK       = (15,  23,  42)
ACCENT     = (5,  150, 105)
BLUE       = (37,  99, 235)
RED        = (220, 38,  38)
SECTION_BG = (236, 253, 245)
LABEL_CLR  = (100, 116, 139)
BORDER_CLR = (203, 213, 225)
WHITE      = (255, 255, 255)
LIGHT_GRAY = (248, 250, 252)
TABLE_ALT  = (241, 245, 249)
TOTAL_BG   = (219, 234, 254)   # blue-100

# ---------------------------------------------------------------------------
# Base PDF class — Discharge Summary
# ---------------------------------------------------------------------------
class DischargePDF(FPDF):
    def __init__(self, hospital_name="", hospital_addr=""):
        super().__init__()
        self.hospital_name = hospital_name
        self.hospital_addr = hospital_addr
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(16, 22, 16)

    def header(self):
        self.set_fill_color(*BLUE)
        self.rect(0, 0, 210, 20, "F")
        self.set_y(3)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*WHITE)
        self.cell(0, 7, self.hospital_name, align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 8)
        self.cell(0, 4, self.hospital_addr, align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*DARK)
        self.ln(5)

    def footer(self):
        self.set_y(-13)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*LABEL_CLR)
        self.cell(0, 5,
                  f"DISCHARGE SUMMARY  |  Confidential Medical Record  |  Page {self.page_no()}",
                  align="C")

    def doc_title(self, title="DISCHARGE SUMMARY"):
        self.set_fill_color(*LIGHT_GRAY)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*DARK)
        self.cell(0, 9, title, align="C", fill=True,
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def section(self, title):
        self.ln(3)
        self.set_fill_color(*SECTION_BG)
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.4)
        self.set_font("Helvetica", "B", 9.5)
        self.set_text_color(*ACCENT)
        self.cell(0, 7, f"  {title}", border="LB", fill=True,
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*DARK)
        self.ln(2)

    def kv(self, label, value, bold_val=False):
        self.set_font("Helvetica", "B", 8.5)
        self.set_text_color(*LABEL_CLR)
        self.cell(52, 5, label + ":")
        self.set_font("Helvetica", "B" if bold_val else "", 9)
        self.set_text_color(*DARK)
        self.multi_cell(0, 5, str(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def kv2(self, l1, v1, l2, v2):
        self.set_font("Helvetica", "B", 8.5)
        self.set_text_color(*LABEL_CLR)
        self.cell(52, 5, l1 + ":")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*DARK)
        self.cell(70, 5, str(v1))
        self.set_font("Helvetica", "B", 8.5)
        self.set_text_color(*LABEL_CLR)
        self.cell(30, 5, l2 + ":")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*DARK)
        self.cell(0, 5, str(v2), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def paragraph(self, text, indent=0):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*DARK)
        if indent:
            self.set_x(self.l_margin + indent)
        self.multi_cell(0, 5, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def bullet_list(self, items):
        for item in items:
            self.set_font("Helvetica", "", 9)
            self.set_text_color(*DARK)
            self.cell(6, 5, "-")
            self.multi_cell(0, 5, item, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def flag_box(self, message):
        """Red-bordered box highlighting missing / incomplete data."""
        self.ln(2)
        self.set_fill_color(255, 235, 235)
        self.set_draw_color(*RED)
        self.set_line_width(0.5)
        self.set_font("Helvetica", "B", 8.5)
        self.set_text_color(*RED)
        self.multi_cell(0, 6, f"  INCOMPLETE DATA NOTE: {message}",
                        border=1, fill=True,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*DARK)
        self.ln(2)

    def sig_row(self):
        self.ln(10)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*DARK)
        self.cell(87, 5, "_____________________________")
        self.cell(87, 5, "_____________________________", align="R",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.cell(87, 5, "Treating Doctor (Signature & Stamp)")
        self.cell(87, 5, "Authorised Hospital Signatory", align="R",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)


# ---------------------------------------------------------------------------
# Base PDF class — Final Bill
# ---------------------------------------------------------------------------
class BillPDF(FPDF):
    def __init__(self, hospital_name="", gstin=""):
        super().__init__()
        self.hospital_name = hospital_name
        self.gstin = gstin
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(16, 22, 16)

    def header(self):
        self.set_fill_color(*DARK)
        self.rect(0, 0, 210, 20, "F")
        self.set_y(3)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*WHITE)
        self.cell(0, 7, self.hospital_name, align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 8)
        self.cell(0, 4, f"GSTIN: {self.gstin}", align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*DARK)
        self.ln(5)

    def footer(self):
        self.set_y(-13)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*LABEL_CLR)
        self.cell(0, 5,
                  f"FINAL HOSPITAL BILL  |  Page {self.page_no()}  |  This is a computer-generated bill",
                  align="C")

    def bill_header_box(self, data: dict):
        self.set_fill_color(*LIGHT_GRAY)
        self.set_draw_color(*BORDER_CLR)
        self.set_line_width(0.3)
        self.rect(self.l_margin, self.get_y(), 178, 32, "FD")
        y = self.get_y() + 2

        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*DARK)

        fields = [
            [("Bill No.", data["bill_no"]), ("Bill Date", data["bill_date"]), ("TPA", data["tpa"])],
            [("UHID", data["uhid"]), ("Category", data["category"]), ("TPA ID", data.get("tpa_id", "N/A"))],
            [("Patient Name", data["patient_name"]), ("Age/Sex", data["age_sex"]), ("Policy No.", data.get("policy_no", "N/A"))],
            [("Adm. Date", data["adm_date"]), ("Dis. Date", data["dis_date"]), ("Duration", data["duration"])],
        ]
        col_w = [60, 60, 58]
        for row in fields:
            self.set_y(y)
            self.set_x(self.l_margin + 2)
            for (lbl, val), w in zip(row, col_w):
                self.set_font("Helvetica", "B", 8)
                self.set_text_color(*LABEL_CLR)
                self.cell(20, 4, lbl + ":")
                self.set_font("Helvetica", "", 8.5)
                self.set_text_color(*DARK)
                self.cell(w - 20, 4, str(val))
            y += 7

        self.set_y(y + 2)

    def service_table(self, rows: list):
        # Header
        self.set_fill_color(*DARK)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 9)
        self.cell(90, 7, "  Service / Description", fill=True)
        self.cell(32, 7, "Gross Amt (Rs.)", align="R", fill=True)
        self.cell(28, 7, "Discount (Rs.)", align="R", fill=True)
        self.cell(28, 7, "Net Amt (Rs.)", align="R", fill=True,
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        for i, (service, gross, disc, net) in enumerate(rows):
            self.set_fill_color(*TABLE_ALT if i % 2 else WHITE)
            self.set_text_color(*DARK)
            self.set_font("Helvetica", "", 9)
            self.cell(90, 6, f"  {service}", fill=True)
            self.set_font("Helvetica", "", 9)
            self.cell(32, 6, f"{gross:,.2f}", align="R", fill=True)
            self.cell(28, 6, f"{disc:,.2f}", align="R", fill=True)
            self.cell(28, 6, f"{net:,.2f}", align="R", fill=True,
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def total_section(self, gross, discount, net, advance, tpa_amt, patient_amt=0):
        self.ln(2)
        self.set_draw_color(*BORDER_CLR)
        self.set_line_width(0.3)
        lines = [
            ("Total Gross Bill Amount",      gross,       False),
            ("Total Discount Amount",         discount,    False),
            ("Net Billable Amount",           net,         False),
            ("Advance Received",              advance,     False),
            ("Net TPA / Corporate Amount",    tpa_amt,     True),
            ("Amount To Be Received from Patient", patient_amt, False),
        ]
        for label, amount, bold in lines:
            if bold:
                self.set_fill_color(*TOTAL_BG)
                self.set_font("Helvetica", "B", 9.5)
            else:
                self.set_fill_color(*LIGHT_GRAY)
                self.set_font("Helvetica", "", 9)
            self.set_text_color(*DARK)
            self.cell(130, 6, f"  {label}", fill=True)
            self.set_font("Helvetica", "B" if bold else "", 9)
            self.cell(48, 6, f"Rs. {amount:,.2f}", align="R", fill=True,
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _s(obj):
    """Sanitise unicode chars to latin-1 safe equivalents."""
    table = {
        "\u2014": "--", "\u2013": "-", "\u2019": "'", "\u2018": "'",
        "\u201c": '"',  "\u201d": '"', "\u2022": "*", "\u00b0": " deg",
        "\u00b2": "2",  "\u00b3": "3",
    }
    if isinstance(obj, str):
        for c, r in table.items():
            obj = obj.replace(c, r)
        return obj
    if isinstance(obj, dict):
        return {k: _s(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_s(i) for i in obj]
    return obj


# ===========================================================================
# PATIENT DATA
# ===========================================================================

CASES = [
    # =========================================================================
    # GROUP A — Original 5 ABHA Registry Patients
    # =========================================================================

    # -------------------------------------------------------------------------
    # 1. Rahul Sharma — Acute Calculous Cholecystitis → Lap. Cholecystectomy
    #    MISSING: ICD-10 PCS procedure code not mentioned in discharge doc
    # -------------------------------------------------------------------------
    {
        "id": "rahul_sharma",
        "abha_id": "12-3456-7890-1234",
        "hospital": "Ruby Hall Clinic",
        "hospital_addr": "40 Sassoon Road, Pune, Maharashtra 411001",
        "hospital_gstin": "27AACCR2044B1ZP",
        "rohini_id": "H-RH-PUN-003",
        "tpa": "Medi Assist Insurance TPA Pvt Ltd",
        "tpa_id": "TPA-MA-2024-8821",
        "patient_name": "Rahul Sharma",
        "age_sex": "45 Y / Male",
        "dob": "12-Aug-1980",
        "policy_no": "HDFC123456",
        "insured_card_id": "INS789456",
        "insurance_company": "HDFC ERGO General Insurance",
        "doctor_name": "Dr. Sanjay Kulkarni",
        "doctor_reg": "MH-47821",
        "specialization": "General & Laparoscopic Surgery",
        "uhid": "RHC2026001234",
        "bill_no": "IP26001235",
        "adm_date": "18-Mar-2026",
        "dis_date": "21-Mar-2026",
        "duration": "3 days",
        "ward": "Surgical Ward B (Bed 204)",
        # Discharge summary content
        "diagnosis_final": "Acute Calculous Cholecystitis with multiple gallstones (largest 14 mm)",
        "icd10_final": "K81.0 -- Acute cholecystitis",
        "procedure": "Laparoscopic Cholecystectomy (4-port technique)",
        "icd10_pcs": "",   # INTENTIONALLY BLANK — system should flag this
        "admission_complaints": [
            "Severe right upper quadrant pain radiating to the right shoulder for 18 hours",
            "Nausea with two episodes of vomiting",
            "Low-grade fever (99.4 deg F)",
            "Previous 3 similar milder episodes over past 6 months",
        ],
        "course_in_hospital": (
            "Patient admitted through Emergency with acute RUQ pain. USG Abdomen confirmed "
            "acute cholecystitis -- thickened gallbladder wall (7 mm), pericholecystic fluid, "
            "multiple gallstones (largest 14 mm). WBC: 13,400 (neutrophilia). LFT: mildly elevated "
            "bilirubin (1.8 mg/dL). IV fluids and IV Cefuroxime 1.5g BD administered. "
            "Patient stabilised and taken for elective laparoscopic cholecystectomy under GA "
            "on Day 2 (19-Mar-2026). Four-port technique used. Gallbladder excised without "
            "spillage. Cholangiogram: no CBD stones. Post-op recovery uneventful. "
            "Started on oral liquids Day 1 post-op, regular diet Day 2. Drain removed Day 2. "
            "Discharged Day 3 in stable condition."
        ),
        "investigations": [
            "USG Abdomen (18-Mar): Acute cholecystitis, multiple gallstones, CBD not dilated",
            "CBC: WBC 13,400, Hb 14.2 g/dL",
            "LFT: Bilirubin 1.8 mg/dL, AST/ALT mildly elevated",
            "Lipase: 42 U/L (normal)",
            "ECG: Normal sinus rhythm",
            "Histopathology (gallbladder specimen): Chronic calculous cholecystitis with acute exacerbation",
        ],
        "discharge_meds": [
            "Tab. Cefuroxime 500 mg BD x 5 days",
            "Tab. Pantoprazole 40 mg OD x 2 weeks",
            "Tab. Paracetamol 650 mg SOS (for pain)",
            "Syrup Lactulose 15 mL BD x 5 days",
        ],
        "condition_at_discharge": "Haemodynamically stable. Afebrile. Wound healthy.",
        "follow_up": "Review at OPD after 7 days. Suture removal at Day 7.",
        "missing_flag": "Procedure ICD-10 PCS code not documented. Surgeon registration no. missing from this summary.",
        # Bill rows: (service, gross, discount, net)
        "bill_rows": [
            ("Room Charges (Surgical Ward x 3 days)",    9000.0,   720.0,   8280.0),
            ("Admission Charges",                          500.0,     0.0,    500.0),
            ("Operation Theatre Charges",               28000.0,  2240.0,  25760.0),
            ("Surgeon Fees (Dr. Kulkarni)",              20000.0,  1600.0,  18400.0),
            ("Anaesthesia Fees",                          8000.0,   640.0,   7360.0),
            ("Pharmacy & Consumables",                    9500.0,   760.0,   8740.0),
            ("Pathology (CBC, LFT, Lipase)",              3800.0,   304.0,   3496.0),
            ("Radiology (USG Abdomen)",                   2200.0,   176.0,   2024.0),
            ("Histopathology",                            1800.0,   144.0,   1656.0),
            ("Dietician & Nursing Charges",               1200.0,     0.0,   1200.0),
            ("Medical Records",                            500.0,     0.0,    500.0),
        ],
        "advance": 5000.0,
        "patient_pay": 0.0,
    },

    # -------------------------------------------------------------------------
    # 2. Priya Menon — Hypertensive Emergency + Hypertensive Retinopathy
    #    MISSING: Policy number and TPA details not in discharge summary
    # -------------------------------------------------------------------------
    {
        "id": "priya_menon",
        "abha_id": "14-2345-6789-0011",
        "hospital": "Manipal Hospital Whitefield",
        "hospital_addr": "Whitefield Main Road, Bengaluru, Karnataka 560066",
        "hospital_gstin": "29AACCM8044R1ZP",
        "rohini_id": "H-MH-BLR-011",
        "tpa": "Max Bupa TPA Services Ltd",
        "tpa_id": "TPA-MB-2024-4422",
        "patient_name": "Priya Menon",
        "age_sex": "33 Y / Female",
        "dob": "25-Mar-1992",
        "policy_no": "MAXB987654",      # not in discharge doc intentionally
        "insured_card_id": "INS112233",
        "insurance_company": "Max Bupa Health Insurance",
        "doctor_name": "Dr. Kavitha Nair",
        "doctor_reg": "KA-52341",
        "specialization": "Internal Medicine & Hypertension",
        "uhid": "MHW2026005678",
        "bill_no": "IP26005679",
        "adm_date": "12-Mar-2026",
        "dis_date": "16-Mar-2026",
        "duration": "4 days",
        "ward": "Medical Ward C (Bed 318)",
        "diagnosis_final": "Hypertensive Emergency with Grade III Hypertensive Retinopathy; Hypertensive Nephropathy (Stage 2 CKD, newly diagnosed)",
        "icd10_final": "I10 -- Essential (primary) hypertension; H35.0 -- Hypertensive retinopathy",
        "procedure": "Medical Management (IV antihypertensives, ophthalmology review, nephrology review)",
        "icd10_pcs": "N/A -- Medical management only",
        "admission_complaints": [
            "Severe headache (VAS 9/10) for 6 hours -- occipital, throbbing",
            "Blurred vision and scotomas in both eyes for 3 hours",
            "BP on arrival: 218/132 mmHg",
            "Known hypertensive for 3 years, defaulted on medications for 4 months",
        ],
        "course_in_hospital": (
            "Patient admitted with hypertensive emergency (BP 218/132 mmHg). "
            "IV Labetalol infusion commenced targeting BP reduction of 20-25% in first hour. "
            "Ophthalmology review (Day 1): Grade III hypertensive retinopathy -- bilateral "
            "flame-shaped haemorrhages, soft exudates, arteriolar narrowing. "
            "Nephrology review (Day 1): Creatinine 1.6 mg/dL, eGFR 52 mL/min, proteinuria 2+ "
            "-- Stage 2 CKD newly diagnosed. "
            "BP progressively controlled over 48 hours. Switched to oral agents Day 2. "
            "Neurology: CT Brain (plain): No haemorrhage, no infarct. "
            "Echocardiography: Concentric LVH (LV mass index 128 g/m2), EF preserved (62%). "
            "BP at discharge: 148/88 mmHg (satisfactory). "
            "Patient counselled extensively on medication compliance and lifestyle modification."
        ),
        "investigations": [
            "BP monitoring: 218/132 on arrival, controlled to 148/88 by Day 4",
            "CT Brain (plain, 12-Mar): No bleed / no infarct",
            "Fundoscopy: Grade III hypertensive retinopathy bilateral",
            "Echo: Concentric LVH, EF 62%, no regional wall motion abnormality",
            "Creatinine: 1.6 mg/dL (Day 1), 1.4 mg/dL (Day 4)",
            "Urine R/M: Proteinuria 2+, no casts",
            "Electrolytes: Na 138, K 3.9",
            "Thyroid (TSH): 3.2 mIU/L (normal -- secondary HTN excluded)",
        ],
        "discharge_meds": [
            "Tab. Amlodipine 10 mg OD",
            "Tab. Telmisartan 80 mg OD",
            "Tab. Metoprolol Succinate 50 mg OD",
            "Tab. Chlorthalidone 12.5 mg OD",
            "Tab. Aspirin 75 mg OD",
            "Tab. Atorvastatin 40 mg OD at night",
        ],
        "condition_at_discharge": "BP controlled (148/88 mmHg). No focal neuro deficit. Vision improving.",
        "follow_up": "Ophthalmology OPD: 7 days. Nephrology OPD: 2 weeks. Medicine OPD: 1 month.",
        "missing_flag": "Policy number and TPA details not documented in this discharge summary. Employee ID absent.",
        "bill_rows": [
            ("Room Charges (Medical Ward x 4 days)",     12000.0,   960.0,  11040.0),
            ("IV Medications (Labetalol, IV fluids)",      8500.0,   680.0,   7820.0),
            ("Oral Medications (4 days)",                  3200.0,   256.0,   2944.0),
            ("Pathology (CBC, RFT, Electrolytes, TSH)",    5600.0,   448.0,   5152.0),
            ("Radiology (CT Brain, Chest X-ray)",          9500.0,   760.0,   8740.0),
            ("Echocardiography",                           4500.0,   360.0,   4140.0),
            ("Ophthalmology Consultation + Fundoscopy",    3000.0,   240.0,   2760.0),
            ("Nephrology Consultation",                    2000.0,   160.0,   1840.0),
            ("Nursing & Monitoring Charges",               3500.0,   280.0,   3220.0),
            ("Dietician + Medical Records",                1200.0,     0.0,   1200.0),
        ],
        "advance": 8000.0,
        "patient_pay": 0.0,
    },

    # -------------------------------------------------------------------------
    # 3. Arun Patel — Diabetic Foot Ulcer (Wagner Grade 2), Debridement
    #    MISSING: HbA1c value not in summary; chronic DM management section incomplete
    # -------------------------------------------------------------------------
    {
        "id": "arun_patel",
        "abha_id": "18-9876-5432-1001",
        "hospital": "Apollo Hospitals",
        "hospital_addr": "Plot No. 1A, Bhat, Near Gandhinagar, Ahmedabad, Gujarat 382428",
        "hospital_gstin": "24AACCA4532K1ZS",
        "rohini_id": "H-AP-AMD-007",
        "tpa": "Star TPA Services Ltd",
        "tpa_id": "TPA-ST-2024-7733",
        "patient_name": "Arun Patel",
        "age_sex": "60 Y / Male",
        "dob": "04-Nov-1965",
        "policy_no": "STAR556677",
        "insured_card_id": "INS334455",
        "insurance_company": "Star Health and Allied Insurance",
        "doctor_name": "Dr. Viral Shah",
        "doctor_reg": "GJ-38901",
        "specialization": "Plastic & Reconstructive Surgery; Diabetology",
        "uhid": "APH2026008821",
        "bill_no": "IP26008822",
        "adm_date": "08-Mar-2026",
        "dis_date": "18-Mar-2026",
        "duration": "10 days",
        "ward": "Surgical Ward A -- then Diabetic Foot Care Unit",
        "diagnosis_final": "Diabetic Foot Ulcer Right Plantar (Wagner Grade 2) with Cellulitis; Type 2 Diabetes Mellitus (Poorly Controlled); Hypertension",
        "icd10_final": "E11.621 -- Type 2 diabetes mellitus with foot ulcer; L03.115 -- Cellulitis of right foot",
        "procedure": "Surgical Wound Debridement + Split-thickness Skin Grafting (STSG) right foot",
        "icd10_pcs": "0HBGXZZ -- Excision of Right Foot Skin, External Approach",
        "admission_complaints": [
            "Non-healing ulcer on plantar aspect of right foot for 3 weeks",
            "Surrounding redness, swelling and warmth spreading up to ankle for 5 days",
            "Foul-smelling discharge from ulcer",
            "Numbness in both feet for 2 years (peripheral neuropathy)",
        ],
        "course_in_hospital": (
            "Patient admitted with Wagner Grade 2 diabetic foot ulcer (2.5 x 3 cm) on right "
            "plantar surface with surrounding cellulitis extending to ankle. Blood sugar on "
            "admission: 368 mg/dL. Blood cultures sent. "
            "HbA1c: [VALUE NOT DOCUMENTED IN THIS SUMMARY -- SEE INVESTIGATION REPORT]. "  # intentional omission
            "Wound culture: Staphylococcus aureus (MSSA) + E. coli mixed infection. "
            "IV Ceftriaxone 1g BD + IV Metronidazole 500 mg TDS commenced. "
            "Doppler USG right lower limb: Peripheral arterial disease (mildly reduced ABI 0.8), "
            "no critical ischaemia. "
            "Diabetology review: Insulin intensive regimen commenced (Glargine 18 units nocte + "
            "Aspart sliding scale). Sugar controlled to 120-180 mg/dL range by Day 3. "
            "Surgical debridement performed under spinal anaesthesia on Day 4 (11-Mar-2026). "
            "Healthy granulation tissue by Day 7. Split-thickness skin graft (STSG) applied "
            "Day 8 (15-Mar-2026). Graft take: 90%. "
            "Discharged Day 10 with wound VAC (vacuum-assisted closure) in place."
        ),
        "investigations": [
            "Blood Sugar (admission): 368 mg/dL; (at discharge): 142 mg/dL",
            "HbA1c: Sent -- value not transcribed in this summary",     # intentional gap
            "CBC: WBC 17,200 (neutrophilia), Hb 11.8 g/dL",
            "CRP: 186 mg/L (Day 1), 34 mg/L (Day 8)",
            "Creatinine: 1.2 mg/dL (borderline)",
            "Wound culture: MSSA + E. coli -- sensitive to Ceftriaxone",
            "Blood culture: No growth (x2)",
            "Doppler USG right LL: ABI 0.8, no critical ischaemia",
            "X-ray right foot: No osteomyelitis",
        ],
        "discharge_meds": [
            "Tab. Amoxicillin-Clavulanate 625 mg BD x 14 days",
            "Tab. Metronidazole 400 mg TDS x 7 days",
            "Inj. Insulin Glargine 18 units nocte (subcutaneous)",
            "Tab. Metformin 500 mg BD (to be restarted after creatinine recheck)",
            "Tab. Amlodipine 5 mg OD + Tab. Losartan 50 mg OD",
            "Tab. Pregabalin 75 mg BD (neuropathic pain)",
            "Local wound care: daily dressing with Betadine + saline irrigation",
        ],
        "condition_at_discharge": "Wound healing satisfactorily. Graft take 90%. Sugars controlled. Afebrile.",
        "follow_up": "Diabetic Foot Clinic: Day 3, Day 7, Day 14. HbA1c recheck at 3 months.",
        "missing_flag": "HbA1c value missing from discharge summary. Duration of DM and HTN not documented. Chronic medication list incomplete.",
        "bill_rows": [
            ("Room Charges (Surgical Ward x 6 days)",      18000.0,  1440.0,  16560.0),
            ("Diabetic Foot Care Unit (x 4 days)",         20000.0,  1600.0,  18400.0),
            ("Surgical Debridement (OT Charges)",          22000.0,  1760.0,  20240.0),
            ("Split-Thickness Skin Graft (OT Charges)",    18000.0,  1440.0,  16560.0),
            ("Surgeon Fees (Dr. Shah)",                    25000.0,  2000.0,  23000.0),
            ("Anaesthesia Fees (Spinal)",                   8000.0,   640.0,   7360.0),
            ("IV Antibiotics (Ceftriaxone, Metronidazole)", 14000.0, 1120.0,  12880.0),
            ("Insulin Therapy & Glucose Monitoring",        6500.0,   520.0,   5980.0),
            ("Diabetology Consultation",                    3000.0,   240.0,   2760.0),
            ("Wound VAC Dressing & Consumables",            8000.0,   640.0,   7360.0),
            ("Pathology (CBC, CRP, Blood Culture, HbA1c)", 7800.0,   624.0,   7176.0),
            ("Radiology (X-ray, Doppler USG)",              4500.0,   360.0,   4140.0),
        ],
        "advance": 10000.0,
        "patient_pay": 0.0,
    },

    # -------------------------------------------------------------------------
    # 4. Sunita Rao — Symptomatic Uterine Fibroids → Lap. Myomectomy
    #    MISSING: Employee ID missing, surgeon qualification not in doc
    # -------------------------------------------------------------------------
    {
        "id": "sunita_rao",
        "abha_id": "21-1111-2222-3333",
        "hospital": "Yashoda Hospitals",
        "hospital_addr": "Raj Bhavan Road, Somajiguda, Hyderabad, Telangana 500082",
        "hospital_gstin": "36AACCY4411H1ZT",
        "rohini_id": "H-YH-HYD-004",
        "tpa": "Health India TPA Services",
        "tpa_id": "TPA-HI-2024-5566",
        "patient_name": "Sunita Rao",
        "age_sex": "37 Y / Female",
        "dob": "19-Jul-1988",
        "policy_no": "NIAC445566",
        "insured_card_id": "INS556677",
        "insurance_company": "New India Assurance",
        "doctor_name": "Dr. Nirmala Desai",
        "doctor_reg": "TS-44321",
        "specialization": "Gynaecology & Minimally Invasive Surgery",
        "uhid": "YH2026009934",
        "bill_no": "IP26009935",
        "adm_date": "20-Mar-2026",
        "dis_date": "24-Mar-2026",
        "duration": "4 days",
        "ward": "Gynaecology Ward (Bed 512)",
        "diagnosis_final": "Symptomatic Intramural Uterine Fibroids (Multiple, Largest 6.2 cm); Secondary Anaemia",
        "icd10_final": "D25.1 -- Intramural leiomyoma of uterus; D64.9 -- Anaemia, unspecified",
        "procedure": "Laparoscopic Myomectomy (Intramural, 3 Fibroids Removed)",
        "icd10_pcs": "0UB10ZZ -- Excision of Uterus, Open Approach",
        "admission_complaints": [
            "Heavy menstrual bleeding (menorrhagia) for 8 months -- soaking 8-10 pads/day",
            "Dysmenorrhoea (VAS 8/10) since 1 year",
            "Pelvic pressure/fullness and urinary frequency",
            "Symptoms progressively worsening, failed medical management (Norethisterone 5 mg BD)",
        ],
        "course_in_hospital": (
            "Patient admitted for elective laparoscopic myomectomy. Pre-op Hb: 8.4 g/dL (anaemia "
            "secondary to menorrhagia). Pre-op blood transfusion: 1 unit PRBC (Day 1) -- Hb improved "
            "to 9.8 g/dL. "
            "Laparoscopic myomectomy performed Day 2 under GA. Three intramural fibroids excised: "
            "6.2 cm (anterior wall), 3.8 cm (fundus), 2.1 cm (posterior wall). "
            "Estimated blood loss: 380 mL. Cell-saver used. Uterus closed in 2 layers. "
            "No intra-operative complications. "
            "Post-op: IV Cefazolin 1g TDS x 2 days. IV tranexamic acid. "
            "All specimens sent for histopathology. "
            "Hb at discharge: 9.2 g/dL (improving). Resumed oral diet Day 2 post-op."
            "Discharged Day 4 in stable condition."
        ),
        "investigations": [
            "TVS USG (15-Mar-2026): Multiple intramural fibroids, uterus 14 x 10 cm, largest 6.2 cm anterior",
            "MRI Pelvis: Intramural fibroids confirmed, no submucosal extension",
            "CBC: Hb 8.4 g/dL (pre-op), 9.2 g/dL (discharge), WBC normal",
            "Blood Group & Cross-match: B+ (1 unit PRBC transfused)",
            "LFT, RFT, Coagulation: Normal",
            "Pap Smear: Normal",
            "Histopathology (fibroids): Leiomyoma -- no malignancy",
        ],
        "discharge_meds": [
            "Tab. Ferrous Sulphate 200 mg BD x 3 months",
            "Tab. Vitamin C 500 mg OD (with iron)",
            "Cap. Doxycycline 100 mg BD x 5 days",
            "Tab. Paracetamol + Ibuprofen (SOS for pain)",
            "Tab. Progesterone 200 mg OD x 3 months (to prevent recurrence)",
        ],
        "condition_at_discharge": "Haemodynamically stable. Minimal post-op pain. Wound healthy.",
        "follow_up": "OPD review Day 7 (wound check). Repeat USG at 6 weeks.",
        "missing_flag": "Employee ID (EMP4022) not present in this document. Doctor qualification not mentioned. Pre-auth policy number mismatch risk.",
        "bill_rows": [
            ("Room Charges (Gynaecology Ward x 4 days)",  12000.0,   960.0,  11040.0),
            ("Operation Theatre Charges (Lap. Myomectomy)", 32000.0, 2560.0, 29440.0),
            ("Gynaecologist Fees (Dr. Desai)",             25000.0,  2000.0,  23000.0),
            ("Anaesthesia Fees",                             9000.0,   720.0,   8280.0),
            ("Blood & Blood Products (1 unit PRBC)",         5500.0,   440.0,   5060.0),
            ("Pharmacy & Consumables",                      11000.0,   880.0,  10120.0),
            ("Pathology + Histopathology",                   6800.0,   544.0,   6256.0),
            ("Radiology (USG, MRI Pelvis)",                 16000.0,  1280.0,  14720.0),
            ("Cell Saver Usage",                             4000.0,   320.0,   3680.0),
            ("Nursing & Monitoring Charges",                 3500.0,   280.0,   3220.0),
        ],
        "advance": 8000.0,
        "patient_pay": 0.0,
    },

    # -------------------------------------------------------------------------
    # 5. Vikram Singh — Unstable Angina / CAD 3-Vessel → CABG (3-vessel)
    #    MISSING: ICU days count missing from discharge; stent info blank
    # -------------------------------------------------------------------------
    {
        "id": "vikram_singh",
        "abha_id": "31-4444-5555-6666",
        "hospital": "Sawai Man Singh Medical College & Hospital",
        "hospital_addr": "SMS Hospital, Jaipur, Rajasthan 302004",
        "hospital_gstin": "08AACCS9981G1ZR",
        "rohini_id": "H-SMS-JAI-001",
        "tpa": "FHPL TPA Services",
        "tpa_id": "TPA-FH-2024-2233",
        "patient_name": "Vikram Singh",
        "age_sex": "51 Y / Male",
        "dob": "30-Jan-1975",
        "policy_no": "ORIE223344",
        "insured_card_id": "INS778899",
        "insurance_company": "Oriental Insurance Company",
        "doctor_name": "Dr. Rajendra Sharma",
        "doctor_reg": "RJ-23456",
        "specialization": "Cardiothoracic & Vascular Surgery",
        "uhid": "SMS2026011023",
        "bill_no": "IP26011024",
        "adm_date": "15-Mar-2026",
        "dis_date": "22-Mar-2026",
        "duration": "7 days",
        "ward": "CTVS Ward -- ICU (Days 1-3) -- Step-down Ward (Days 4-7)",
        "diagnosis_final": "Coronary Artery Disease -- 3 Vessel Disease (LAD 90%, LCx 80%, RCA 70% stenosis); Type 2 Diabetes Mellitus; Hypertension",
        "icd10_final": "I25.10 -- Atherosclerotic heart disease of native coronary artery without angina pectoris",
        "procedure": "Off-pump Coronary Artery Bypass Grafting (OPCAB) -- 3 Grafts (LIMA-LAD, SVG-LCx, SVG-RCA)",
        "icd10_pcs": "021209W -- Bypass Coronary Artery, Three Sites from Aorta with Autologous Venous Tissue, Open Approach",
        "admission_complaints": [
            "Progressive exertional chest pain (CCS Class III) for 3 months",
            "Recent rest angina 2 episodes in past 1 week",
            "Dyspnoea on exertion (NYHA Class II-III)",
            "Known diabetic and hypertensive for 8 years",
        ],
        "course_in_hospital": (
            "Patient admitted with unstable angina and CAD triple vessel disease on coronary "
            "angiography (Day 1). Cardiothoracic surgery review recommended OPCAB. "
            "Pre-op optimisation: IV Heparin infusion, Ticagrelor and Aspirin continued, "
            "glycaemic control with insulin. Echo: EF 45%, anterior hypokinesia. "
            "OPCAB performed Day 3 (17-Mar-2026) -- 3 grafts: LIMA to LAD, SVG to LCx, "
            "SVG to RCA. Off-pump (beating heart technique) -- no CPB. "
            "Post-operative ICU course: [ICU stay duration not documented in this summary]. "  # intentional gap
            "Extubated at 6 hours post-op. Chest drains removed Day 2 post-op. "
            "Haemodynamically stable from Day 2. "
            "Blood sugar controlled (120-180 mg/dL). "
            "Mobilised Day 3 post-op. ECG: SR, no new changes. "
            "Discharged Day 7 in stable condition with cardiac rehabilitation referral."
        ),
        "investigations": [
            "Coronary Angiography: LAD 90%, LCx 80%, RCA 70% -- triple vessel disease",
            "Echocardiography: EF 45%, anterior hypokinesia, no effusion",
            "Carotid Doppler: No significant stenosis",
            "CBC: Hb 12.8 g/dL, WBC normal, Platelets 1.9 lakh",
            "HbA1c: 8.4% (poorly controlled DM pre-admission)",
            "Creatinine: 1.1 mg/dL, LFT: Normal",
            "Coagulation: PT/APTT within normal limits",
            "Post-op ECG (Day 5): Normal sinus rhythm, no new ischaemic changes",
        ],
        "discharge_meds": [
            "Tab. Aspirin 75 mg OD (lifelong)",
            "Tab. Ticagrelor 90 mg BD x 1 year",
            "Tab. Atorvastatin 80 mg OD at night (lifelong)",
            "Tab. Metoprolol Succinate 50 mg OD",
            "Tab. Ramipril 5 mg OD",
            "Inj. Insulin Glargine 22 units nocte",
            "Tab. Pantoprazole 40 mg OD",
            "Tab. Pregabalin 75 mg OD (neuropathy)",
        ],
        "condition_at_discharge": "Haemodynamically stable. Wounds healing. Sinus rhythm. Sugars controlled.",
        "follow_up": "Cardiothoracic OPD: Day 7. Cardiologist: Day 14. Cardiac Rehabilitation: Enrolment at discharge.",
        "missing_flag": "ICU duration post-operatively not documented. Pre-auth stent/implant details section blank (CABG not stent, but system may flag). Exact LOS in ICU missing from bill breakdown.",
        "bill_rows": [
            ("ICU Charges (CTVS ICU -- exact days not specified)",  45000.0, 3600.0, 41400.0),
            ("Step-down Ward (x 4 days, Rs. 5,000/day)",           20000.0, 1600.0, 18400.0),
            ("CTVS OT Charges (OPCAB)",                            80000.0, 6400.0, 73600.0),
            ("Surgeon Fees (Dr. Sharma, CTVS)",                    60000.0, 4800.0, 55200.0),
            ("Cardiac Anaesthesia Fees",                            25000.0, 2000.0, 23000.0),
            ("LIMA Graft + SVG Harvest + Consumables",              35000.0, 2800.0, 32200.0),
            ("Coronary Angiography",                                20000.0, 1600.0, 18400.0),
            ("IV Medications (Heparin, Ticagrelor, Insulin)",       18000.0, 1440.0, 16560.0),
            ("Ventilator Charges",                                  12000.0,  960.0, 11040.0),
            ("Pathology (CBC, HbA1c, LFT, Coag, Blood Cultures)",   9500.0,  760.0,  8740.0),
            ("Echo + ECG (x3) + Carotid Doppler",                   8000.0,  640.0,  7360.0),
            ("Cardiac Physiotherapy (3 sessions)",                   4500.0,  360.0,  4140.0),
            ("Medical Records + Admission",                          1000.0,    0.0,  1000.0),
        ],
        "advance": 20000.0,
        "patient_pay": 0.0,
    },

    # =========================================================================
    # GROUP B — New Case Patients (matching generate_new_cases.py pre-auths)
    # =========================================================================

    # -------------------------------------------------------------------------
    # 6. Ramesh Kumar Sharma — STEMI, PTCA with DES (LAD), Apollo Hyderabad
    # -------------------------------------------------------------------------
    {
        "id": "ramesh_sharma",
        "abha_id": "41-5555-6666-7777",
        "hospital": "Apollo Hospitals",
        "hospital_addr": "Jubilee Hills, Hyderabad, Telangana 500033",
        "hospital_gstin": "36AACCA4532K1ZR",
        "rohini_id": "H-AP-HYD-001",
        "tpa": "Medi Assist Insurance TPA Pvt Ltd",
        "tpa_id": "TPA-MA-2024-8831",
        "patient_name": "Ramesh Kumar Sharma",
        "age_sex": "54 Y / Male",
        "dob": "15-Mar-1970",
        "policy_no": "HDFC-HI-2024-88321",
        "insured_card_id": "IC-88321-A",
        "insurance_company": "HDFC ERGO General Insurance",
        "doctor_name": "Dr. Suresh Reddy",
        "doctor_reg": "TS-56001",
        "specialization": "Interventional Cardiology",
        "uhid": "APH2026012001",
        "bill_no": "IP26012002",
        "adm_date": "28-Mar-2026",
        "dis_date": "31-Mar-2026",
        "duration": "3 days",
        "ward": "CCU (All 3 days)",
        "diagnosis_final": "ST-Elevation Myocardial Infarction (Anterior Wall STEMI) -- Post-Primary PTCA with DES",
        "icd10_final": "I21.0 -- Acute transmural myocardial infarction of anterior wall",
        "procedure": "Primary PTCA with Drug-Eluting Stent (DES, Xience Sierra 3.5x28mm) -- Proximal LAD",
        "icd10_pcs": "027034Z -- Dilation of Coronary Artery with Drug-eluting Intraluminal Device",
        "admission_complaints": [
            "Severe crushing chest pain radiating to left arm and jaw for 3 hours",
            "Profuse sweating (diaphoresis), breathlessness, nausea",
            "BP on arrival: 90/60 mmHg (cardiogenic shock)",
            "No prior cardiac history; Type 2 Diabetes Mellitus on Metformin",
        ],
        "course_in_hospital": (
            "Patient presented with acute anterior STEMI and cardiogenic shock. "
            "Cardiac catheterisation lab activated immediately. Coronary angiography: "
            "LAD total proximal occlusion (TIMI 0 flow), LCx and RCA non-significant. "
            "Primary PCI performed: Xience Sierra DES (3.5 x 28 mm) deployed in proximal LAD. "
            "Post-PCI TIMI 3 flow achieved. IABP inserted for haemodynamic support. "
            "Transferred to CCU for monitoring. IABP weaned Day 2. "
            "Echo (post-PCI, Day 2): EF improved from 38% to 45%, anterior hypokinesia residual. "
            "Dual antiplatelet therapy (Aspirin + Ticagrelor) maintained. "
            "IABP removed Day 2. Ambulated Day 3. Discharged Day 3 on DAPT and cardiac rehab referral."
        ),
        "investigations": [
            "ECG (12-lead): ST elevation V1-V4 (anterior STEMI)",
            "Troponin I: 12.4 ng/mL (markedly elevated)",
            "CK-MB: 185 U/L",
            "Coronary Angiography: LAD proximal total occlusion",
            "Echo (post-PCI): EF 45%, anterior hypokinesia",
            "Blood Sugar: 224 mg/dL (admission), 148 mg/dL (discharge)",
            "Creatinine: 1.1 mg/dL (stable)",
            "CBC: Hb 13.8, WBC 11,200 (reactive leucocytosis)",
        ],
        "discharge_meds": [
            "Tab. Aspirin 75 mg OD (lifelong)",
            "Tab. Ticagrelor 90 mg BD x 1 year",
            "Tab. Atorvastatin 80 mg OD at night",
            "Tab. Metoprolol Succinate 25 mg OD",
            "Tab. Ramipril 2.5 mg OD",
            "Tab. Pantoprazole 40 mg OD",
            "Tab. Metformin 500 mg BD (restart after cardiology review)",
        ],
        "condition_at_discharge": "Haemodynamically stable. IABP removed. No further ischaemia. Good stent deployment.",
        "follow_up": "Cardiology OPD: Day 7. Repeat Echo: 6 weeks. Cardiac Rehabilitation enrolment.",
        "missing_flag": "None -- all major fields present. Minor: exact IABP duration (hours) not stated.",
        "bill_rows": [
            ("CCU Charges (x 3 days, Rs. 8,000/day)",      24000.0, 1920.0, 22080.0),
            ("Cath Lab / Coronary Angiography",             35000.0, 2800.0, 32200.0),
            ("Primary PCI Procedure Charges",               25000.0, 2000.0, 23000.0),
            ("Drug-Eluting Stent (Xience Sierra 3.5x28mm)", 45000.0, 3600.0, 41400.0),
            ("IABP Insertion + Rental (2 days)",            18000.0, 1440.0, 16560.0),
            ("Cardiologist Fees (Dr. Reddy)",               30000.0, 2400.0, 27600.0),
            ("IV Medications (Heparin, Ticagrelor load)",   12000.0,  960.0, 11040.0),
            ("Investigations (ECG, Echo, Troponin, CBC)",   18000.0, 1440.0, 16560.0),
            ("Nursing & Monitoring (CCU)",                   6000.0,  480.0,  5520.0),
            ("Pharmacy & Consumables",                        5000.0,  400.0,  4600.0),
        ],
        "advance": 10000.0,
        "patient_pay": 0.0,
    },

    # -------------------------------------------------------------------------
    # 7. Sunita Devi Agarwal — TKR Left Knee, Fortis Gurugram
    # -------------------------------------------------------------------------
    {
        "id": "sunita_agarwal",
        "abha_id": "42-6666-7777-8888",
        "hospital": "Fortis Memorial Research Institute",
        "hospital_addr": "Sector 44, Gurugram, Haryana 122002",
        "hospital_gstin": "06AACCF2233K1ZP",
        "rohini_id": "H-FR-GGN-005",
        "tpa": "Max Bupa TPA Services Ltd",
        "tpa_id": "TPA-MB-2025-4451",
        "patient_name": "Sunita Devi Agarwal",
        "age_sex": "62 Y / Female",
        "dob": "22-Jul-1963",
        "policy_no": "MAX-GHI-2023-44512",
        "insured_card_id": "IC-44512-B",
        "insurance_company": "Max Bupa Health Insurance",
        "doctor_name": "Dr. Ashok Rajgopal",
        "doctor_reg": "HR-41230",
        "specialization": "Joint Replacement & Orthopaedic Surgery",
        "uhid": "FMRI2026014501",
        "bill_no": "IP26014502",
        "adm_date": "05-Apr-2026",
        "dis_date": "10-Apr-2026",
        "duration": "5 days",
        "ward": "Orthopaedic Ward (Bed 418)",
        "diagnosis_final": "Primary Osteoarthritis of Left Knee -- Grade IV (Kellgren-Lawrence); Type 2 Diabetes Mellitus; Hypertension",
        "icd10_final": "M17.12 -- Primary osteoarthritis of left knee",
        "procedure": "Total Knee Replacement (TKR) -- Left Knee (Stryker Triathlon CR System, Cemented)",
        "icd10_pcs": "0SRC0J9 -- Replacement of Left Knee Joint with Synthetic Substitute, Cemented",
        "admission_complaints": [
            "Severe bilateral knee pain (L>R) for 2 years, unable to walk >100 m",
            "Morning stiffness >30 minutes",
            "Failed 18 months conservative management (physiotherapy, NSAIDs, injections)",
            "Background: DM (HbA1c 7.2%), HTN (controlled on Amlodipine + Losartan)",
        ],
        "course_in_hospital": (
            "Patient admitted for elective TKR left knee. Pre-op HbA1c 7.2% (well controlled). "
            "Blood pressure 128/78 mmHg pre-op. "
            "TKR performed Day 1 under spinal anaesthesia. Stryker Triathlon CR system cemented. "
            "Cell-saver used -- autologous blood recovery 380 mL. "
            "TXA (Tranexamic Acid) protocol applied. "
            "Post-op: CPM started Day 1, physiotherapy commenced Day 1 (quad sets, SLR). "
            "Enoxaparin 40 mg OD commenced (DVT prophylaxis) from Day 1. "
            "Wound drain removed Day 2. Ambulation with walker Day 2. "
            "Stair climbing achieved Day 4. "
            "Post-op X-ray: Good implant alignment, components well-seated. "
            "Discharged Day 5 with home physiotherapy plan and outpatient physiotherapy referral."
        ),
        "investigations": [
            "Pre-op X-ray Left Knee (wt-bearing): Grade IV OA, bone-on-bone medial compartment",
            "Post-op X-ray (Day 2): Implant well-aligned, satisfactory component position",
            "CBC: Hb 11.2 (pre-op), 10.1 (post-op Day 2) -- improving",
            "HbA1c: 7.2% (pre-op, well controlled)",
            "Coagulation: PT/APTT normal",
            "ECG + Echo (pre-op): Normal SR, EF 62%",
            "Blood Group + Cross-match: A+ (no transfusion needed, cell-saver used)",
        ],
        "discharge_meds": [
            "Inj. Enoxaparin 40 mg SC OD x 4 weeks (DVT prophylaxis)",
            "Tab. Paracetamol 650 mg TDS x 2 weeks",
            "Tab. Celecoxib 200 mg BD x 2 weeks (anti-inflammatory)",
            "Tab. Pantoprazole 40 mg OD x 4 weeks",
            "Tab. Metformin 1000 mg BD (continue)",
            "Tab. Amlodipine 5 mg OD + Tab. Losartan 50 mg OD (continue)",
            "Calcium + Vitamin D3 supplement OD x 3 months",
        ],
        "condition_at_discharge": "Wound healthy. Walking with walker. Pain controlled. Sugars within target.",
        "follow_up": "Ortho OPD: Day 7 (wound/staple check), Day 30 (functional assessment).",
        "missing_flag": "None -- all pre-auth fields matched. Minor: Cell-saver blood volume not linked to bill.",
        "bill_rows": [
            ("Room Charges (Ortho Ward x 5 days, Rs. 5,000/day)",  25000.0, 2000.0, 23000.0),
            ("OT Charges (TKR)",                                    55000.0, 4400.0, 50600.0),
            ("Knee Implant (Stryker Triathlon CR System)",         110000.0, 8800.0,101200.0),
            ("Surgeon Fees (Dr. Rajgopal)",                         60000.0, 4800.0, 55200.0),
            ("Anaesthesia Fees (Spinal)",                           20000.0, 1600.0, 18400.0),
            ("Physiotherapy (In-patient, 5 sessions)",               7500.0,  600.0,  6900.0),
            ("Cell Saver Usage",                                     5000.0,  400.0,  4600.0),
            ("Enoxaparin + DVT Prophylaxis",                         4500.0,  360.0,  4140.0),
            ("Medicines & Consumables",                             13500.0, 1080.0, 12420.0),
            ("Investigations (X-ray x2, Labs, Echo, ECG)",          14500.0, 1160.0, 13340.0),
        ],
        "advance": 15000.0,
        "patient_pay": 0.0,
    },

    # -------------------------------------------------------------------------
    # 8. Vikram Singh Chauhan — Acute Appendicitis, Lap. Appendicectomy, Manipal Bengaluru
    # -------------------------------------------------------------------------
    {
        "id": "vikram_chauhan",
        "abha_id": "43-7777-8888-9999",
        "hospital": "Manipal Hospitals",
        "hospital_addr": "Whitefield Road, Whitefield, Bengaluru, Karnataka 560066",
        "hospital_gstin": "29AACCM8044R1ZQ",
        "rohini_id": "H-MN-BLR-012",
        "tpa": "Star TPA Services Ltd",
        "tpa_id": "TPA-ST-2025-1983",
        "patient_name": "Vikram Singh Chauhan",
        "age_sex": "28 Y / Male",
        "dob": "05-Nov-1997",
        "policy_no": "STAR-HI-2025-19834",
        "insured_card_id": "IC-19834-C",
        "insurance_company": "Star Health and Allied Insurance",
        "doctor_name": "Dr. Priya Menon",
        "doctor_reg": "KA-38901",
        "specialization": "General & Laparoscopic Surgery",
        "uhid": "MNH2026016003",
        "bill_no": "IP26016004",
        "adm_date": "28-Mar-2026",
        "dis_date": "31-Mar-2026",
        "duration": "3 days",
        "ward": "Surgical Ward A (Bed 204)",
        "diagnosis_final": "Acute Appendicitis (Non-perforated) -- Post-Laparoscopic Appendicectomy",
        "icd10_final": "K35.2 -- Acute appendicitis without perforation",
        "procedure": "Laparoscopic Appendicectomy (3-port technique)",
        "icd10_pcs": "0DTJ4ZZ -- Resection of Appendix, Percutaneous Endoscopic Approach",
        "admission_complaints": [
            "Acute onset right iliac fossa pain for 12 hours",
            "Fever (101 deg F), nausea, one episode of vomiting",
            "Loss of appetite; Rebound tenderness at McBurney's point",
        ],
        "course_in_hospital": (
            "Patient admitted via Emergency with Alvarado Score 8 (high probability appendicitis). "
            "USG confirmed dilated non-compressible appendix (9 mm). "
            "IV antibiotics commenced pre-op (Cefuroxime + Metronidazole). "
            "Emergency laparoscopic appendicectomy performed same evening under GA. "
            "3-port technique. Appendix: mildly inflamed, no perforation, no peritoneal contamination. "
            "Specimen sent for histopathology. "
            "Post-op course uneventful. Tolerated oral fluids 6 hours post-op. "
            "Mobilised next morning. Discharged Day 3. "
            "Histopathology (awaiting at discharge): Acute appendicitis confirmed."
        ),
        "investigations": [
            "USG Abdomen: Appendix 9 mm diameter, non-compressible, periappendiceal fat stranding",
            "CBC: WBC 14,800 (neutrophilia), CRP 82 mg/L",
            "Alvarado Score: 8",
            "LFT, RFT: Normal",
            "Urine R/M: Normal (renal colic excluded)",
        ],
        "discharge_meds": [
            "Tab. Cefuroxime 500 mg BD x 5 days",
            "Tab. Metronidazole 400 mg TDS x 5 days",
            "Tab. Paracetamol 650 mg SOS",
            "Syrup Lactulose 15 mL OD x 3 days",
        ],
        "condition_at_discharge": "Afebrile. Wound healthy. Tolerating normal diet. No peritoneal signs.",
        "follow_up": "OPD Day 7 (wound check + histopathology review).",
        "missing_flag": "None -- all fields complete. Histopathology result pending (will be added to case post-discharge).",
        "bill_rows": [
            ("Room Charges (Twin-sharing x 3 days, Rs. 1,800/day)",  5400.0,  432.0,  4968.0),
            ("Admission Charges",                                       300.0,    0.0,   300.0),
            ("OT Charges (Laparoscopic)",                            28000.0, 2240.0, 25760.0),
            ("Surgeon Fees (Dr. Menon)",                             18000.0, 1440.0, 16560.0),
            ("Anaesthesia Fees (GA)",                                 8000.0,  640.0,  7360.0),
            ("IV Antibiotics & Consumables",                          5800.0,  464.0,  5336.0),
            ("Pharmacy",                                              2800.0,  224.0,  2576.0),
            ("Histopathology (Appendix specimen)",                    1200.0,   96.0,  1104.0),
            ("Pathology (CBC, CRP, LFT)",                             3400.0,  272.0,  3128.0),
            ("Radiology (USG Abdomen)",                               1600.0,  128.0,  1472.0),
            ("Medical Records",                                        500.0,    0.0,   500.0),
        ],
        "advance": 5000.0,
        "patient_pay": 0.0,
    },

    # -------------------------------------------------------------------------
    # 9. Kavita Rani Mishra — Severe CAP Pneumonia, Medical Mgmt, Medanta Gurugram
    # -------------------------------------------------------------------------
    {
        "id": "kavita_mishra",
        "abha_id": "44-8888-9999-0000",
        "hospital": "Medanta The Medicity",
        "hospital_addr": "CH Baktawar Singh Road, Sector 38, Gurugram, Haryana 122001",
        "hospital_gstin": "06AACCM9981G1ZR",
        "rohini_id": "H-MD-GGN-002",
        "tpa": "Bajaj Allianz TPA Services",
        "tpa_id": "TPA-BA-2024-6712",
        "patient_name": "Kavita Rani Mishra",
        "age_sex": "45 Y / Female",
        "dob": "30-Jan-1981",
        "policy_no": "BAJAJ-AHI-2024-67123",
        "insured_card_id": "IC-67123-D",
        "insurance_company": "Bajaj Allianz Health Insurance",
        "doctor_name": "Dr. Randeep Guleria",
        "doctor_reg": "DL-20140",
        "specialization": "Pulmonology & Critical Care Medicine",
        "uhid": "MED2026017002",
        "bill_no": "IP26017003",
        "adm_date": "28-Mar-2026",
        "dis_date": "04-Apr-2026",
        "duration": "7 days",
        "ward": "HDU (Days 1-2) -- Medical Ward (Days 3-7)",
        "diagnosis_final": "Severe Community-Acquired Pneumonia (Right Lower Lobe Lobar Pneumonia, Streptococcus pneumoniae) -- CURB-65 Score 3; Type 2 Diabetes Mellitus (Poorly Controlled, HbA1c 9.8%)",
        "icd10_final": "J18.1 -- Lobar pneumonia, unspecified organism; E11 -- Type 2 diabetes mellitus",
        "procedure": "Medical Management (HDU + IV antibiotics + Glycaemic control)",
        "icd10_pcs": "N/A -- Medical management",
        "admission_complaints": [
            "High-grade fever 103 deg F for 4 days, chills and rigors",
            "Progressive breathlessness at rest (MMRC Grade 3)",
            "Productive cough with purulent yellow-green sputum",
            "Right-sided pleuritic chest pain",
            "SpO2 88% on room air on arrival",
        ],
        "course_in_hospital": (
            "Patient admitted with severe CAP (CURB-65 score 3) and hypoxaemia (SpO2 88%). "
            "Admitted to HDU. IV Piperacillin-Tazobactam 4.5g TDS + IV Azithromycin 500 mg OD commenced. "
            "Oxygen therapy (target SpO2 >94%): 4L/min initially, weaned to 2L/min by Day 3. "
            "Sputum culture (Day 3): Streptococcus pneumoniae -- sensitive to Pip-Taz. "
            "Blood cultures (x2): No growth. "
            "Glycaemic control: Insulin sliding scale, blood sugar 120-200 mg/dL range achieved by Day 2. "
            "HbA1c on admission: 9.8% (poorly controlled). "
            "Clinical improvement: Afebrile by Day 3. Breathing improved. CXR Day 5: Clearing consolidation. "
            "Stepped down to oral Amoxicillin-Clavulanate + Azithromycin Day 5. "
            "Stepped down from HDU to medical ward Day 3. "
            "Discharged Day 7 on room air (SpO2 97%)."
        ),
        "investigations": [
            "CXR (admission): Right lower lobe consolidation with air bronchograms",
            "CXR (Day 5): Partial resolution of consolidation",
            "HRCT Chest: Lobar consolidation RLL + small right pleural effusion",
            "CBC: WBC 18,600 (neutrophilia) Day 1 -> 9,200 Day 7",
            "CRP: 248 mg/L (Day 1) -> 42 mg/L (Day 7)",
            "Procalcitonin: 3.8 ng/mL (Day 1) -> 0.4 ng/mL (Day 6)",
            "Sputum culture: Streptococcus pneumoniae (sensitive to Pip-Taz)",
            "Blood cultures (x2): No growth",
            "Blood Sugar (admission): 312 mg/dL; HbA1c: 9.8%",
            "ABG (Day 1): pH 7.38, PaO2 68, PCO2 36 (Type I respiratory failure)",
        ],
        "discharge_meds": [
            "Tab. Amoxicillin-Clavulanate 625 mg BD x 7 days",
            "Tab. Azithromycin 500 mg OD x 5 days",
            "Tab. Montelukast 10 mg OD x 2 weeks",
            "Inj. Insulin Glargine 20 units nocte (insulin for DM)",
            "Tab. Metformin 500 mg BD",
            "Tab. Sitagliptin 100 mg OD",
        ],
        "condition_at_discharge": "Afebrile. SpO2 97% on room air. Breathing comfortable. Sugars controlled.",
        "follow_up": "Pulmonology OPD: 2 weeks. Repeat CXR: 6 weeks. Diabetology: 4 weeks (HbA1c reassessment).",
        "missing_flag": "None -- all fields complete. Note: HbA1c was 9.8% vs pre-auth which may not have stated this -- flagged for claim.",
        "bill_rows": [
            ("HDU Charges (x 2 days, Rs. 6,000/day)",              12000.0,  960.0, 11040.0),
            ("Medical Ward (x 5 days, Rs. 2,200/day)",             11000.0,  880.0, 10120.0),
            ("IV Piperacillin-Tazobactam (7 days)",                16000.0, 1280.0, 14720.0),
            ("IV Azithromycin (4 days) + Oral (3 days)",            8000.0,  640.0,  7360.0),
            ("Insulin Sliding Scale + Monitoring",                   3500.0,  280.0,  3220.0),
            ("Oxygen Therapy & Nebulisation (7 days)",               4000.0,  320.0,  3680.0),
            ("IV Fluids & Consumables",                               5000.0,  400.0,  4600.0),
            ("Chest Physiotherapy (5 sessions)",                      3500.0,  280.0,  3220.0),
            ("Pathology (CBC x3, CRP, PCT, Blood Culture, ABG)",     9500.0,  760.0,  8740.0),
            ("Radiology (CXR x2, HRCT Chest)",                       6500.0,  520.0,  5980.0),
            ("Sputum Culture + Sensitivity",                          1500.0,  120.0,  1380.0),
            ("Medical Records + Admission",                            500.0,    0.0,   500.0),
        ],
        "advance": 8000.0,
        "patient_pay": 0.0,
    },

    # -------------------------------------------------------------------------
    # 10. Anjali Reddy — Elective Repeat LSCS (G2P1L1), Rainbow Hyderabad
    # -------------------------------------------------------------------------
    {
        "id": "anjali_reddy",
        "abha_id": "45-9999-0000-1111",
        "hospital": "Rainbow Children's Hospital",
        "hospital_addr": "Road No. 10, Banjara Hills, Hyderabad, Telangana 500034",
        "hospital_gstin": "36AACCR4567K1ZT",
        "rohini_id": "H-RB-HYD-008",
        "tpa": "Health India TPA Services",
        "tpa_id": "TPA-NI-2022-3321",
        "patient_name": "Anjali Reddy",
        "age_sex": "29 Y / Female",
        "dob": "12-Jun-1996",
        "policy_no": "NIAC-GHI-2022-33214",
        "insured_card_id": "IC-33214-E",
        "insurance_company": "New India Assurance",
        "doctor_name": "Dr. Mohana Venugopal",
        "doctor_reg": "TS-62300",
        "specialization": "Obstetrics & Gynaecology (High-Risk Pregnancy)",
        "uhid": "RCH2026018001",
        "bill_no": "IP26018002",
        "adm_date": "01-Apr-2026",
        "dis_date": "06-Apr-2026",
        "duration": "5 days",
        "ward": "Maternity Ward (Bed 312) + NBSU (Newborn)",
        "diagnosis_final": "Pregnancy 38 Weeks, G2P1L1 -- Delivered by Elective Repeat LSCS; Baby Girl 2.92 kg, APGAR 9/10",
        "icd10_final": "O82.0 -- Delivery by elective Caesarean section; Z37.0 -- Single live birth",
        "procedure": "Elective Lower Segment Caesarean Section (Pfannenstiel incision, Spinal Anaesthesia)",
        "icd10_pcs": "10D00Z1 -- Extraction of Products of Conception, Low Cervical, Open Approach",
        "admission_complaints": [
            "38 weeks gestation, G2P1L1A0 -- for elective repeat LSCS",
            "Previous LSCS (2023) for foetal distress",
            "No active labour. No leaking. Regular foetal movements.",
            "Pre-op assessment: BP 114/72, FHR 142/min, CTG reactive",
        ],
        "course_in_hospital": (
            "Patient admitted at 38 weeks for elective repeat LSCS. Pre-op assessment complete. "
            "Nil by mouth from midnight. "
            "Elective LSCS performed 01-Apr-2026 at 09:30 hrs under spinal anaesthesia. "
            "Pfannenstiel incision. Lower uterine segment transverse incision. "
            "Baby girl delivered at 09:42 hrs. Birth weight: 2.92 kg. APGAR 9/10 at 1 min, 10/10 at 5 min. "
            "Cord blood sent. Placenta delivered complete. "
            "Uterus closed in 2 layers. Fascia and skin closed. EBL: 650 mL. "
            "IV Oxytocin 20 units in 500 mL RL post-delivery. "
            "Post-op: Epidural analgesia 12 hours, then IV Paracetamol + Diclofenac. "
            "Breastfeeding initiated 4 hours post-op. "
            "Baby: NBSU observation for 24 hours (routine), discharged with mother. "
            "Mother: Afebrile, BP stable, uterus well-contracted. "
            "Early ambulation (4-6 hours post-op). Diet resumed Day 2. "
            "Discharged Day 5 with both mother and baby in good condition."
        ),
        "investigations": [
            "USG (26-Mar-2026): Single live foetus, cephalic, AFI 14 cm, EFW 2.9 kg, placenta anterior",
            "CTG (pre-op): Reactive",
            "CBC: Hb 10.8 g/dL (pre-op), 9.4 g/dL (post-op Day 2)",
            "Blood Group: B+ ve",
            "Coagulation: PT/APTT normal",
            "HBsAg: Negative, HIV: Non-reactive, VDRL: Non-reactive",
            "Baby weight: 2.92 kg, APGAR 9/10 (1 min), 10/10 (5 min)",
            "Cord blood: Group B+ ve",
        ],
        "discharge_meds": [
            "Tab. Ferrous Sulphate 200 mg BD x 3 months",
            "Tab. Paracetamol 650 mg TDS x 5 days",
            "Tab. Ibuprofen 400 mg BD x 5 days (post-op pain)",
            "Tab. Pantoprazole 40 mg OD x 2 weeks",
            "Tab. Vitamin D3 60,000 IU weekly x 4 weeks",
            "Syrup Lactulose 15 mL BD x 1 week",
            "For baby: Vitamin D3 drops 400 IU OD",
        ],
        "condition_at_discharge": "Mother: Stable, BP normal, lochia normal, wound healthy, breastfeeding well. Baby: Healthy girl, weight 2.88 kg.",
        "follow_up": "OBG OPD: Day 7 (wound check). Paediatric OPD: Day 7 (baby weight check).",
        "missing_flag": "None -- complete. Package charges should match pre-auth maternity bundle estimate.",
        "bill_rows": [
            ("Room Charges (Maternity Ward x 5 days, Rs. 2,500/day)",  12500.0, 1000.0, 11500.0),
            ("LSCS OT Charges",                                         30000.0, 2400.0, 27600.0),
            ("Obstetrician Fees (Dr. Venugopal)",                       25000.0, 2000.0, 23000.0),
            ("Anaesthesia Fees (Spinal)",                               10000.0,  800.0,  9200.0),
            ("Neonatologist Charges",                                    5000.0,  400.0,  4600.0),
            ("NBSU (Newborn Special Care -- Day 1)",                     4000.0,  320.0,  3680.0),
            ("Medicines & Consumables (Oxytocin, IV fluids, sutures)",   8500.0,  680.0,  7820.0),
            ("Investigations (USG, CTG, CBC, Coag, Blood Group, VDRL)",  6000.0,  480.0,  5520.0),
            ("Nursing & Monitoring (Mother + Baby)",                      4000.0,  320.0,  3680.0),
            ("Dietician + Medical Records",                               1200.0,    0.0,  1200.0),
        ],
        "advance": 10000.0,
        "patient_pay": 0.0,
    },
]


# ===========================================================================
# Generators
# ===========================================================================

def build_discharge_summary(c: dict, out_dir: str):
    pdf = DischargePDF(
        hospital_name=c["hospital"],
        hospital_addr=c["hospital_addr"],
    )
    pdf.add_page()
    pdf.doc_title("DISCHARGE SUMMARY")

    # Patient & admission info
    pdf.section("PATIENT & ADMISSION DETAILS")
    pdf.kv2("UHID", c["uhid"], "Bill No.", c["bill_no"])
    pdf.kv2("Patient Name", c["patient_name"], "Age / Sex", c["age_sex"])
    pdf.kv2("Date of Birth", c["dob"], "ABHA ID", c["abha_id"])
    pdf.kv2("Date of Admission", c["adm_date"], "Date of Discharge", c["dis_date"])
    pdf.kv2("Duration of Stay", c["duration"], "Ward / Bed", c["ward"])
    pdf.kv2("Treating Doctor", c["doctor_name"], "Reg. No.", c["doctor_reg"])
    pdf.kv("Specialization", c["specialization"])

    # Insurance (intentionally incomplete for some patients)
    pdf.section("INSURANCE / TPA DETAILS")
    pdf.kv2("Insurance Company", c["insurance_company"], "TPA", c["tpa"])
    pdf.kv2("Policy No.", c.get("policy_no", ""),  "Insured Card ID", c.get("insured_card_id", ""))
    pdf.kv("ROHINI ID", c["rohini_id"])

    # Admission complaints
    pdf.section("PRESENTING COMPLAINTS (AT ADMISSION)")
    pdf.bullet_list(c["admission_complaints"])

    # Diagnosis
    pdf.section("FINAL DIAGNOSIS")
    pdf.kv("Diagnosis", c["diagnosis_final"], bold_val=True)
    pdf.kv("ICD-10 Code", c["icd10_final"])

    # Procedure
    pdf.section("PROCEDURE / TREATMENT")
    pdf.kv("Procedure", c["procedure"])
    if c["icd10_pcs"] and c["icd10_pcs"] != "":
        pdf.kv("ICD-10 PCS Code", c["icd10_pcs"])
    else:
        pdf.flag_box("ICD-10 PCS procedure code not documented in this record.")

    # Course in hospital
    pdf.section("COURSE IN HOSPITAL")
    pdf.paragraph(c["course_in_hospital"])

    # Investigations
    pdf.section("KEY INVESTIGATIONS")
    pdf.bullet_list(c["investigations"])

    # Discharge medications
    pdf.section("DISCHARGE MEDICATIONS")
    pdf.bullet_list(c["discharge_meds"])

    # Condition at discharge + follow-up
    pdf.section("CONDITION AT DISCHARGE & FOLLOW-UP")
    pdf.kv("Condition at Discharge", c["condition_at_discharge"])
    pdf.kv("Follow-up Instructions", c["follow_up"])

    # Missing data flag box
    if c.get("missing_flag") and "None" not in c["missing_flag"]:
        pdf.flag_box(c["missing_flag"])

    pdf.sig_row()

    fname = f"discharge_{c['id']}.pdf"
    pdf.output(os.path.join(out_dir, fname))
    print(f"  [Discharge] {fname}")


def build_final_bill(c: dict, out_dir: str):
    pdf = BillPDF(
        hospital_name=c["hospital"],
        gstin=c["hospital_gstin"],
    )
    pdf.add_page()

    # Doc title
    pdf.set_fill_color(*LIGHT_GRAY)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 8, "FINAL HOSPITAL BILL", align="C", fill=True,
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

    # Compute totals
    gross   = sum(r[1] for r in c["bill_rows"])
    disc    = sum(r[2] for r in c["bill_rows"])
    net     = sum(r[3] for r in c["bill_rows"])
    advance = c.get("advance", 0.0)
    tpa_amt = net - advance
    pat_amt = c.get("patient_pay", 0.0)

    # Header box
    pdf.bill_header_box({
        "bill_no":       c["bill_no"],
        "bill_date":     c["dis_date"],
        "tpa":           c["tpa"],
        "uhid":          c["uhid"],
        "category":      c["insurance_company"],
        "tpa_id":        c.get("tpa_id", ""),
        "patient_name":  c["patient_name"],
        "age_sex":       c["age_sex"],
        "policy_no":     c.get("policy_no", ""),
        "adm_date":      c["adm_date"],
        "dis_date":      c["dis_date"],
        "duration":      c["duration"],
    })

    pdf.ln(3)

    # Service table
    pdf.service_table(c["bill_rows"])
    pdf.ln(4)

    # Totals
    pdf.total_section(gross, disc, net, advance, tpa_amt, pat_amt)

    # Footer note
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*LABEL_CLR)
    pdf.multi_cell(0, 5,
        "This bill is subject to approval by the Insurance Company / TPA. "
        "Payment governed by terms and conditions of the policy. "
        "All discounts are as per TPA / corporate agreement rates.",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(12)

    # Signature row
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*DARK)
    pdf.cell(87, 5, "_____________________________")
    pdf.cell(87, 5, "_____________________________", align="R",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(87, 5, "Patient / Insured Signature")
    pdf.cell(87, 5, "Authorised Hospital Signatory", align="R",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    fname = f"bill_{c['id']}.pdf"
    pdf.output(os.path.join(out_dir, fname))
    print(f"  [Bill]      {fname}")


# ===========================================================================
# Main
# ===========================================================================
if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    dis_dir  = os.path.join(base, "discharge_summaries")
    bill_dir = os.path.join(base, "final_bills")
    os.makedirs(dis_dir,  exist_ok=True)
    os.makedirs(bill_dir, exist_ok=True)

    print(f"\nGenerating {len(CASES)} discharge summaries + {len(CASES)} final bills...\n")

    for case in CASES:
        case = _s(case)
        build_discharge_summary(case, dis_dir)
        build_final_bill(case, bill_dir)

    print(f"\nDone.")
    print(f"  Discharge summaries -> {dis_dir}")
    print(f"  Final bills         -> {bill_dir}")
    print(f"\nMissing-data flags per patient:")
    for c in CASES:
        flag = c.get("missing_flag", "")
        status = "OK" if "None" in flag else "FLAGGED"
        print(f"  [{status:7s}] {c['patient_name']:30s} | {flag[:70]}")
