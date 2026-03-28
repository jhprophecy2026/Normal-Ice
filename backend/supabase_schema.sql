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
