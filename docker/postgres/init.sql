-- PostgreSQL initialization script for Game Scheduler

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create database user with limited privileges (already created by default postgres user)
-- The database is already created via POSTGRES_DB environment variable

-- Log successful initialization
SELECT 'Game Scheduler database initialized successfully' AS status;