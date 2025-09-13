-- Initial schema for users, notes and chunks tables

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    language VARCHAR(8) NOT NULL DEFAULT 'en',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notes (
    id VARCHAR PRIMARY KEY,
    title TEXT NOT NULL,
    tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    topic_id VARCHAR NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    file_path TEXT NOT NULL,
    source_url TEXT NULL,
    author TEXT NULL,
    dt TIMESTAMPTZ NULL,
    channel TEXT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    id VARCHAR PRIMARY KEY,
    note_id VARCHAR NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    pos INTEGER NOT NULL,
    anchor TEXT NULL
);

