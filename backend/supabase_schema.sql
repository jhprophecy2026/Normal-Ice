-- ============================================================
-- ClinicalFHIR — Supabase Schema
-- Run this in your Supabase SQL editor once to set up all tables.
-- ============================================================

-- Enable UUID generation
create extension if not exists "pgcrypto";

-- ------------------------------------------------------------
-- patients
-- Master record per patient. Demographics filled incrementally.
-- ------------------------------------------------------------
create table if not exists patients (
    patient_id          text primary key,          -- ABHA / name+dob hash / uuid
    abha_id             text unique,
    name                text,
    age                 integer,
    gender              text,
    date_of_birth       text,
    contact             text,
    insurance_id        text,

    -- Provider info (latest known)
    practitioner_name   text,
    practitioner_npi    text,
    practitioner_id     text,
    organization_name   text,

    -- Accumulated clinical context
    diagnoses           text[]  default '{}',
    icd10_codes         text[]  default '{}',

    created_at          timestamptz default now(),
    updated_at          timestamptz default now()
);

-- ------------------------------------------------------------
-- patient_documents
-- One row per uploaded PDF.
-- ------------------------------------------------------------
create table if not exists patient_documents (
    id                  uuid primary key default gen_random_uuid(),
    patient_id          text not null references patients(patient_id) on delete cascade,
    filename            text not null,
    document_type       text not null,   -- lab_report | prescription
    upload_date         timestamptz default now(),
    extracted_text_preview text
);

-- ------------------------------------------------------------
-- patient_observations
-- Lab test results. Deduplicated on insert.
-- ------------------------------------------------------------
create table if not exists patient_observations (
    id                  uuid primary key default gen_random_uuid(),
    patient_id          text not null references patients(patient_id) on delete cascade,
    document_id         uuid references patient_documents(id) on delete set null,
    test_name           text not null,
    loinc_code          text,
    cpt_code            text,
    value               text,
    unit                text,
    reference_range     text,
    status              text default 'final',
    interpretation      text,
    service_date        text,
    created_at          timestamptz default now()
);

-- ------------------------------------------------------------
-- patient_medications
-- Prescription medications. Deduplicated on insert.
-- ------------------------------------------------------------
create table if not exists patient_medications (
    id                  uuid primary key default gen_random_uuid(),
    patient_id          text not null references patients(patient_id) on delete cascade,
    document_id         uuid references patient_documents(id) on delete set null,
    medication_name     text not null,
    rxnorm_code         text,
    dosage              text,
    frequency           text,
    duration            text,
    route               text,
    instructions        text,
    prescription_date   text,
    created_at          timestamptz default now()
);

-- ------------------------------------------------------------
-- fhir_bundles
-- Every generated FHIR R4 bundle, linked to its document.
-- ------------------------------------------------------------
create table if not exists fhir_bundles (
    id                  uuid primary key default gen_random_uuid(),
    patient_id          text not null references patients(patient_id) on delete cascade,
    document_id         uuid references patient_documents(id) on delete set null,
    document_type       text,
    bundle              jsonb not null,
    created_at          timestamptz default now()
);

-- ------------------------------------------------------------
-- billing_flags
-- Missing/incomplete fields that affect revenue.
-- resolved = true when subsequent upload fills the gap.
-- ------------------------------------------------------------
create table if not exists billing_flags (
    id                  uuid primary key default gen_random_uuid(),
    patient_id          text not null references patients(patient_id) on delete cascade,
    bundle_id           uuid references fhir_bundles(id) on delete cascade,
    field               text not null,
    severity            text not null,   -- critical | warning
    message             text not null,
    resolved            boolean default false,
    resolved_at         timestamptz,
    created_at          timestamptz default now()
);

-- ------------------------------------------------------------
-- Indexes for common query patterns
-- ------------------------------------------------------------
create index if not exists idx_patient_documents_patient   on patient_documents(patient_id);
create index if not exists idx_observations_patient        on patient_observations(patient_id);
create index if not exists idx_medications_patient         on patient_medications(patient_id);
create index if not exists idx_fhir_bundles_patient        on fhir_bundles(patient_id);
create index if not exists idx_billing_flags_patient       on billing_flags(patient_id);
create index if not exists idx_billing_flags_unresolved    on billing_flags(patient_id, resolved) where resolved = false;
create index if not exists idx_patients_abha               on patients(abha_id) where abha_id is not null;

-- ============================================================
-- PRE-AUTHORIZATION TABLES
-- Run this section after the core schema above.
-- ============================================================

-- ------------------------------------------------------------
-- abha_registry
-- Pre-seeded patient demographic + insurance data keyed by ABHA ID.
-- In production this would be fetched live from the ABDM gateway.
-- ------------------------------------------------------------
create table if not exists abha_registry (
    abha_id           text primary key,
    name              text,
    date_of_birth     text,
    gender            text,
    age               integer,
    contact           text,
    address           text,
    blood_group       text,
    policy_no         text,
    insured_card_id   text,
    employee_id       text,
    insurance_company text,
    tpa_name          text,
    diabetes          boolean default false,
    hypertension      boolean default false,
    heart_disease     boolean default false,
    other_conditions  text,
    created_at        timestamptz default now()
);

-- Seed: 5 dummy patients across different insurers
insert into abha_registry (abha_id, name, date_of_birth, gender, age, contact, address, blood_group,
    policy_no, insured_card_id, employee_id, insurance_company, tpa_name,
    diabetes, hypertension, heart_disease, other_conditions)
values
(
    '12-3456-7890-1234', 'Rahul Sharma', '1980-08-12', 'Male', 45,
    '9876543210', 'Flat 4B, Baner Road, Pune, Maharashtra 411045', 'B+',
    'HDFC123456', 'INS789456', 'EMP1023', 'HDFC ERGO General Insurance', 'Medi Assist',
    false, false, false, null
),
(
    '14-2345-6789-0011', 'Priya Menon', '1992-03-25', 'Female', 33,
    '9845001122', 'House 7, Koramangala, Bengaluru, Karnataka 560034', 'O+',
    'MAXB987654', 'INS112233', 'EMP2045', 'Max Bupa Health Insurance', 'Max Bupa TPA',
    false, true, false, 'Mild hypertension since 2020'
),
(
    '18-9876-5432-1001', 'Arun Patel', '1965-11-04', 'Male', 60,
    '9712345678', '12, Satellite Road, Ahmedabad, Gujarat 380015', 'A+',
    'STAR556677', 'INS334455', 'EMP3011', 'Star Health and Allied Insurance', 'Star TPA',
    true, true, false, 'Type 2 Diabetes on Metformin; Hypertension'
),
(
    '21-1111-2222-3333', 'Sunita Rao', '1988-07-19', 'Female', 37,
    '9900112233', 'Plot 22, Jubilee Hills, Hyderabad, Telangana 500033', 'AB-',
    'NIAC445566', 'INS556677', 'EMP4022', 'New India Assurance', 'Health India TPA',
    false, false, false, null
),
(
    '31-4444-5555-6666', 'Vikram Singh', '1975-01-30', 'Male', 51,
    '9811223344', '5, Civil Lines, Jaipur, Rajasthan 302006', 'O-',
    'ORIE223344', 'INS778899', 'EMP5033', 'Oriental Insurance', 'FHPL',
    true, false, true, 'Ischemic heart disease; Type 2 Diabetes'
)
on conflict (abha_id) do nothing;

-- ------------------------------------------------------------
-- pre_auth_requests
-- One row per pre-authorization request.
-- ------------------------------------------------------------
create table if not exists pre_auth_requests (
    id                         uuid primary key default gen_random_uuid(),
    abha_id                    text references abha_registry(abha_id),
    -- Section 1: Patient & Policy
    patient_name               text,
    age                        integer,
    gender                     text,
    date_of_birth              text,
    contact                    text,
    policy_no                  text,
    insured_card_id            text,
    employee_id                text,
    other_insurance            text,
    -- Section 2: Hospital
    hospital_name              text,
    hospital_address           text,
    rohini_id                  text,
    hospital_email             text,
    -- Section 3: Doctor
    doctor_name                text,
    doctor_contact             text,
    -- Section 4: Medical
    presenting_complaints      text,
    duration_of_illness        text,
    date_of_first_consultation text,
    past_history               text,
    provisional_diagnosis      text,
    icd10_diagnosis_code       text,
    clinical_findings          text,
    -- Section 5: Treatment
    line_of_treatment          text,
    surgery_name               text,
    icd10_pcs_code             text,
    -- Section 6: Admission
    admission_date             text,
    admission_time             text,
    admission_type             text,
    -- Section 7: Past medical history
    diabetes                   boolean default false,
    hypertension               boolean default false,
    heart_disease              boolean default false,
    other_conditions           text,
    -- Section 8: Estimated costs (INR)
    room_rent_per_day          numeric,
    icu_charges_per_day        numeric,
    ot_charges                 numeric,
    surgeon_fees               numeric,
    medicines_consumables      numeric,
    investigations             numeric,
    total_estimated_cost       numeric,
    -- Meta
    status                     text default 'draft',
    created_at                 timestamptz default now(),
    updated_at                 timestamptz default now()
);

create index if not exists idx_pre_auth_abha   on pre_auth_requests(abha_id);
create index if not exists idx_pre_auth_status on pre_auth_requests(status);

-- ============================================================
-- MIGRATION: Add new Medi Assist form fields to pre_auth_requests
-- Run this after the original table creation above.
-- ============================================================
alter table pre_auth_requests
    -- Hospital
    add column if not exists hospital_location            text,
    add column if not exists hospital_id                  text,
    -- Patient
    add column if not exists alternate_contact            text,
    add column if not exists age_months                   integer,
    add column if not exists other_insurance_insurer      text,
    add column if not exists other_insurance_details      text,
    add column if not exists family_physician_name        text,
    add column if not exists family_physician_contact     text,
    add column if not exists occupation                   text,
    add column if not exists patient_address              text,
    -- Treatment type checkboxes
    add column if not exists treatment_medical_management boolean default false,
    add column if not exists treatment_surgical           boolean default false,
    add column if not exists treatment_intensive_care     boolean default false,
    add column if not exists treatment_investigation      boolean default false,
    add column if not exists treatment_non_allopathic     boolean default false,
    -- Medical management
    add column if not exists medical_management_details   text,
    add column if not exists route_of_drug_administration text,
    add column if not exists other_treatment_details      text,
    add column if not exists injury_details               text,
    -- Accident
    add column if not exists is_rta                       boolean,
    add column if not exists date_of_injury               text,
    add column if not exists reported_to_police           boolean,
    add column if not exists fir_no                       text,
    add column if not exists substance_abuse              boolean,
    add column if not exists substance_abuse_test_done    boolean,
    -- Maternity
    add column if not exists maternity_g                  text,
    add column if not exists maternity_p                  text,
    add column if not exists maternity_l                  text,
    add column if not exists maternity_a                  text,
    add column if not exists expected_delivery_date       text,
    -- Admission extras
    add column if not exists expected_days_in_hospital    integer,
    add column if not exists days_in_icu                  integer,
    add column if not exists room_type                    text,
    -- Cost breakdown (new fields)
    add column if not exists investigation_diagnostics_cost numeric,
    add column if not exists professional_fees            numeric,
    add column if not exists other_hospital_expenses      numeric,
    add column if not exists package_charges              numeric,
    -- Past history extras with since dates
    add column if not exists diabetes_since               text,
    add column if not exists heart_disease_since          text,
    add column if not exists hypertension_since           text,
    add column if not exists hyperlipidemias              boolean default false,
    add column if not exists hyperlipidemias_since        text,
    add column if not exists osteoarthritis               boolean default false,
    add column if not exists osteoarthritis_since         text,
    add column if not exists asthma_copd                  boolean default false,
    add column if not exists asthma_copd_since            text,
    add column if not exists cancer                       boolean default false,
    add column if not exists cancer_since                 text,
    add column if not exists alcohol_drug_abuse           boolean default false,
    add column if not exists alcohol_drug_abuse_since     text,
    add column if not exists hiv_std                      boolean default false,
    add column if not exists hiv_std_since                text,
    -- Declaration
    add column if not exists doctor_qualification         text,
    add column if not exists doctor_registration_no       text,
    add column if not exists patient_email                text;

-- rename old column other_insurance (was text) to match new boolean + split fields
-- NOTE: if other_insurance already exists as text, cast it: drop and re-add
-- Supabase handles this gracefully with IF NOT EXISTS above.

-- ============================================================
-- ENHANCEMENT REQUESTS
-- Run after pre_auth_requests table exists.
-- ============================================================

create table if not exists enhancement_requests (
    id                            uuid primary key default gen_random_uuid(),
    pre_auth_id                   uuid not null references pre_auth_requests(id) on delete cascade,
    abha_id                       text references abha_registry(abha_id),
    sequence_no                   integer not null default 1,

    -- Reason
    reason                        text not null,
    clinical_justification        text,

    -- Snapshot of original diagnosis at time of enhancement
    original_diagnosis            text,
    original_icd10_code           text,
    original_total_cost           numeric,

    -- Updated diagnosis
    updated_diagnosis             text,
    updated_icd10_code            text,

    -- Updated treatment
    updated_line_of_treatment     text,
    updated_surgery_name          text,
    updated_icd10_pcs_code        text,

    -- Revised cost estimates
    revised_room_rent_per_day     numeric,
    revised_icu_charges_per_day   numeric,
    revised_ot_charges            numeric,
    revised_surgeon_fees          numeric,
    revised_medicines_consumables numeric,
    revised_investigations        numeric,
    revised_total_estimated_cost  numeric,

    -- Meta
    status                        text default 'submitted',  -- draft | submitted | approved | rejected
    tpa_remarks                   text,
    created_at                    timestamptz default now(),
    updated_at                    timestamptz default now()
);

create index if not exists idx_enhancement_pre_auth on enhancement_requests(pre_auth_id);
create index if not exists idx_enhancement_abha     on enhancement_requests(abha_id);
create index if not exists idx_enhancement_status   on enhancement_requests(status);

-- ============================================================
-- DISCHARGE & SETTLEMENT TABLES
-- ============================================================

alter table pre_auth_requests add column if not exists bill_no text unique;

create table if not exists discharge_requests (
    id                      uuid primary key default gen_random_uuid(),
    bill_no                 text not null,
    pre_auth_id             uuid references pre_auth_requests(id) on delete cascade,
    abha_id                 text references abha_registry(abha_id),
    discharge_date          text,
    final_diagnosis         text,
    final_icd10_codes       text,
    procedure_codes         text,
    discharge_summary_text  text,
    room_charges            numeric,
    icu_charges             numeric,
    surgery_charges         numeric,
    medicine_charges        numeric,
    investigation_charges   numeric,
    other_charges           numeric,
    total_bill_amount       numeric,
    revenue_flags           jsonb default '[]',
    status                  text default 'pending',
    created_at              timestamptz default now(),
    updated_at              timestamptz default now()
);

create index if not exists idx_discharge_bill_no  on discharge_requests(bill_no);
create index if not exists idx_discharge_pre_auth on discharge_requests(pre_auth_id);

create table if not exists settlement_requests (
    id                          uuid primary key default gen_random_uuid(),
    bill_no                     text not null,
    pre_auth_id                 uuid references pre_auth_requests(id) on delete cascade,
    discharge_id                uuid references discharge_requests(id),
    abha_id                     text references abha_registry(abha_id),
    pre_auth_approved_amount    numeric,
    claimed_amount              numeric,
    deduction_amount            numeric default 0,
    deduction_reason            text,
    final_settlement_amount     numeric,
    status                      text default 'pending',
    tpa_remarks                 text,
    settlement_date             text,
    created_at                  timestamptz default now(),
    updated_at                  timestamptz default now()
);

create index if not exists idx_settlement_bill_no  on settlement_requests(bill_no);
create index if not exists idx_settlement_pre_auth on settlement_requests(pre_auth_id);

-- ============================================================
-- EPISODE LINKING: tag all clinical records with bill_no
-- This allows querying the full episode history for a case.
-- ============================================================

-- Tag FHIR bundles with the episode bill_no
alter table fhir_bundles add column if not exists bill_no text;

-- Tag uploaded documents with the episode bill_no
alter table patient_documents add column if not exists bill_no text;

-- Tag lab observations with the episode bill_no
alter table patient_observations add column if not exists bill_no text;

-- Tag medications with the episode bill_no
alter table patient_medications add column if not exists bill_no text;

-- Link pre_auth back to the master patients record
alter table pre_auth_requests add column if not exists patient_id text;

-- Direct bill_no on enhancements (avoids a join through pre_auth)
alter table enhancement_requests add column if not exists bill_no text;

-- Indexes for episode-scoped queries
create index if not exists idx_fhir_bundles_bill_no         on fhir_bundles(bill_no)         where bill_no is not null;
create index if not exists idx_patient_documents_bill_no    on patient_documents(bill_no)     where bill_no is not null;
create index if not exists idx_patient_observations_bill_no on patient_observations(bill_no)  where bill_no is not null;
create index if not exists idx_patient_medications_bill_no  on patient_medications(bill_no)   where bill_no is not null;
create index if not exists idx_pre_auth_patient_id          on pre_auth_requests(patient_id)  where patient_id is not null;
create index if not exists idx_enhancement_bill_no          on enhancement_requests(bill_no)  where bill_no is not null;

-- ------------------------------------------------------------
-- bank_statement_uploads
-- Stores Gemini-extracted payment confirmation fields per case
-- ------------------------------------------------------------
create table if not exists bank_statement_uploads (
    id               uuid primary key default gen_random_uuid(),
    bill_no          text not null unique,
    settlement_id    text,
    utr_number       text,
    amount           numeric,
    transaction_date text,
    transaction_type text,
    sender_bank      text,
    sender_account   text,
    receiver_bank    text,
    receiver_account text,
    ifsc_code        text,
    narration        text,
    created_at       timestamptz default now(),
    updated_at       timestamptz default now()
);

create index if not exists idx_bank_statement_bill_no on bank_statement_uploads(bill_no);
