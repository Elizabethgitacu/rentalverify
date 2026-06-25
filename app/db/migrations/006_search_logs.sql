CREATE TABLE IF NOT EXISTS search_logs (
    id SERIAL PRIMARY KEY,
    search_term TEXT NOT NULL,
    search_type TEXT NOT NULL DEFAULT 'Any',
    location TEXT,
    result_status TEXT NOT NULL,
    matched_landlord_id INTEGER REFERENCES landlord_profiles(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

