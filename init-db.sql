-- Rake V1 - PostgreSQL Initialization Script
-- Creates pgvector extension and sets up initial schema

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schema for Rake (optional, can use public)
CREATE SCHEMA IF NOT EXISTS rake;

-- Grant permissions
GRANT ALL ON SCHEMA rake TO rake_user;
GRANT ALL ON SCHEMA public TO rake_user;

-- Set search path
ALTER ROLE rake_user SET search_path TO rake, public;

-- Create simple health check function
CREATE OR REPLACE FUNCTION rake.health_check()
RETURNS TABLE(status text, timestamp timestamptz) AS $$
BEGIN
  RETURN QUERY SELECT 'healthy'::text, now();
END;
$$ LANGUAGE plpgsql;

-- Log initialization
DO $$
BEGIN
  RAISE NOTICE 'Rake V1 database initialized successfully';
END $$;
