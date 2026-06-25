CREATE TABLE IF NOT EXISTS landlord_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    full_name TEXT NOT NULL,
    email TEXT,
    phone_number TEXT NOT NULL,
    national_id_number TEXT NOT NULL,
    m_pesa_number TEXT NOT NULL,
    property_location TEXT NOT NULL,
    ownership_notes TEXT,
    verification_status TEXT NOT NULL DEFAULT 'pending' CHECK (verification_status IN ('pending', 'verified', 'rejected')),
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_landlord_profiles_phone_number ON landlord_profiles (phone_number);
CREATE INDEX IF NOT EXISTS idx_landlord_profiles_national_id_number ON landlord_profiles (national_id_number);
CREATE INDEX IF NOT EXISTS idx_landlord_profiles_m_pesa_number ON landlord_profiles (m_pesa_number);

