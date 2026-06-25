CREATE TABLE IF NOT EXISTS landlord_documents (
    id SERIAL PRIMARY KEY,
    landlord_profile_id INTEGER NOT NULL REFERENCES landlord_profiles(id) ON DELETE CASCADE,
    document_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

