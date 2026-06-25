CREATE TABLE IF NOT EXISTS admin_actions (
    id SERIAL PRIMARY KEY,
    admin_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

