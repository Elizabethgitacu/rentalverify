CREATE TABLE IF NOT EXISTS scam_reports (
    id SERIAL PRIMARY KEY,
    reporter_name TEXT NOT NULL,
    reporter_phone TEXT NOT NULL,
    landlord_name TEXT NOT NULL,
    landlord_phone TEXT,
    national_id_number TEXT,
    m_pesa_number TEXT,
    property_address TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'under_review', 'escalated', 'closed')),
    reference_number TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scam_reports_status ON scam_reports (status);
CREATE INDEX IF NOT EXISTS idx_scam_reports_reference_number ON scam_reports (reference_number);

