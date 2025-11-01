-- ============================================================================
-- Database Initialization Script for ID Verification API
-- ============================================================================
-- This script creates the database schema for the ID Verification API
-- Run automatically by PostgreSQL on first container startup
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- ============================================================================
-- Table: verification_logs
-- Purpose: Store all verification attempts and results
-- ============================================================================
CREATE TABLE IF NOT EXISTS verification_logs (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Verification Details
    verification_id VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL CHECK (status IN ('approved', 'rejected', 'manual_review', 'error')),
    
    -- Confidence Scores (0-100 scale)
    overall_confidence DECIMAL(5,2) CHECK (overall_confidence >= 0 AND overall_confidence <= 100),
    liveness_score DECIMAL(5,2) CHECK (liveness_score >= 0 AND liveness_score <= 100),
    face_match_confidence DECIMAL(5,2) CHECK (face_match_confidence >= 0 AND face_match_confidence <= 100),
    authenticity_score DECIMAL(5,2) CHECK (authenticity_score >= 0 AND authenticity_score <= 100),
    deepfake_confidence DECIMAL(5,2) CHECK (deepfake_confidence >= 0 AND deepfake_confidence <= 100),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    client_ip INET,
    user_agent TEXT,
    api_key_hash VARCHAR(255),
    processing_time_ms INTEGER,
    
    -- Additional data (flexible JSON field)
    metadata JSONB,
    
    -- Audit fields
    deleted_at TIMESTAMP NULL,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- Create indexes for verification_logs
CREATE INDEX idx_verification_id ON verification_logs(verification_id) WHERE is_deleted = FALSE;
CREATE INDEX idx_created_at ON verification_logs(created_at DESC) WHERE is_deleted = FALSE;
CREATE INDEX idx_status ON verification_logs(status) WHERE is_deleted = FALSE;
CREATE INDEX idx_api_key_hash ON verification_logs(api_key_hash) WHERE is_deleted = FALSE;
CREATE INDEX idx_overall_confidence ON verification_logs(overall_confidence) WHERE is_deleted = FALSE;
CREATE INDEX idx_metadata ON verification_logs USING GIN (metadata) WHERE is_deleted = FALSE;
CREATE INDEX idx_client_ip ON verification_logs(client_ip) WHERE is_deleted = FALSE;

-- Add comment to table
COMMENT ON TABLE verification_logs IS 'Stores all identity verification attempts with scores and metadata';

-- ============================================================================
-- Table: api_keys
-- Purpose: Manage API key authentication and permissions
-- ============================================================================
CREATE TABLE IF NOT EXISTS api_keys (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Key Information
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    key_name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_revoked BOOLEAN DEFAULT FALSE,
    
    -- Rate Limiting
    rate_limit_per_minute INTEGER DEFAULT 60 CHECK (rate_limit_per_minute > 0),
    rate_limit_per_hour INTEGER DEFAULT 1000 CHECK (rate_limit_per_hour > 0),
    rate_limit_per_day INTEGER DEFAULT 10000 CHECK (rate_limit_per_day > 0),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    
    -- Usage Statistics
    total_requests INTEGER DEFAULT 0,
    successful_requests INTEGER DEFAULT 0,
    failed_requests INTEGER DEFAULT 0,
    
    -- Additional data
    metadata JSONB,
    
    -- Audit
    created_by VARCHAR(255),
    revoked_at TIMESTAMP,
    revoked_by VARCHAR(255),
    revoked_reason TEXT
);

-- Create indexes for api_keys
CREATE INDEX idx_key_hash ON api_keys(key_hash) WHERE is_active = TRUE AND is_revoked = FALSE;
CREATE INDEX idx_is_active ON api_keys(is_active) WHERE is_revoked = FALSE;
CREATE INDEX idx_last_used_at ON api_keys(last_used_at DESC);
CREATE INDEX idx_expires_at ON api_keys(expires_at) WHERE is_active = TRUE;

-- Add comment to table
COMMENT ON TABLE api_keys IS 'Manages API key authentication, permissions, and rate limiting';

-- ============================================================================
-- Table: rate_limit_events
-- Purpose: Track rate limiting events for monitoring and analytics
-- ============================================================================
CREATE TABLE IF NOT EXISTS rate_limit_events (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Event Details
    api_key_hash VARCHAR(255),
    client_ip INET,
    endpoint VARCHAR(255),
    
    -- Timestamps
    event_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    
    -- Counts
    request_count INTEGER NOT NULL,
    limit_exceeded BOOLEAN DEFAULT FALSE,
    
    -- Additional data
    metadata JSONB
);

-- Create indexes for rate_limit_events
CREATE INDEX idx_rate_limit_api_key ON rate_limit_events(api_key_hash, event_timestamp DESC);
CREATE INDEX idx_rate_limit_client_ip ON rate_limit_events(client_ip, event_timestamp DESC);
CREATE INDEX idx_rate_limit_timestamp ON rate_limit_events(event_timestamp DESC);

-- Add comment to table
COMMENT ON TABLE rate_limit_events IS 'Tracks rate limiting events for monitoring and compliance';

-- ============================================================================
-- Table: audit_logs
-- Purpose: Comprehensive audit trail for security and compliance
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Audit Information
    event_type VARCHAR(100) NOT NULL,
    event_action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    
    -- User/System Information
    actor VARCHAR(255),
    actor_ip INET,
    api_key_hash VARCHAR(255),
    
    -- Event Details
    event_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    
    -- Request/Response
    request_data JSONB,
    response_data JSONB,
    
    -- Additional context
    metadata JSONB
);

-- Create indexes for audit_logs
CREATE INDEX idx_audit_timestamp ON audit_logs(event_timestamp DESC);
CREATE INDEX idx_audit_event_type ON audit_logs(event_type);
CREATE INDEX idx_audit_actor ON audit_logs(actor);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_api_key ON audit_logs(api_key_hash);

-- Add comment to table
COMMENT ON TABLE audit_logs IS 'Complete audit trail for security, compliance, and debugging';

-- ============================================================================
-- Functions and Triggers
-- ============================================================================

-- Function: Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger: Update updated_at on verification_logs
CREATE TRIGGER update_verification_logs_updated_at 
    BEFORE UPDATE ON verification_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger: Update updated_at on api_keys
CREATE TRIGGER update_api_keys_updated_at 
    BEFORE UPDATE ON api_keys
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function: Soft delete verification logs
CREATE OR REPLACE FUNCTION soft_delete_verification_log()
RETURNS TRIGGER AS $$
BEGIN
    NEW.deleted_at = CURRENT_TIMESTAMP;
    NEW.is_deleted = TRUE;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ============================================================================
-- Views for Analytics
-- ============================================================================

-- View: Daily verification statistics
CREATE OR REPLACE VIEW daily_verification_stats AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_verifications,
    COUNT(*) FILTER (WHERE status = 'approved') as approved,
    COUNT(*) FILTER (WHERE status = 'rejected') as rejected,
    COUNT(*) FILTER (WHERE status = 'manual_review') as manual_review,
    COUNT(*) FILTER (WHERE status = 'error') as errors,
    AVG(overall_confidence) as avg_confidence,
    AVG(processing_time_ms) as avg_processing_time_ms
FROM verification_logs
WHERE is_deleted = FALSE
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- View: API key usage statistics
CREATE OR REPLACE VIEW api_key_usage_stats AS
SELECT 
    k.key_name,
    k.total_requests,
    k.successful_requests,
    k.failed_requests,
    k.last_used_at,
    COUNT(v.id) as recent_verifications,
    AVG(v.overall_confidence) as avg_confidence
FROM api_keys k
LEFT JOIN verification_logs v ON v.api_key_hash = k.key_hash 
    AND v.created_at > NOW() - INTERVAL '7 days'
    AND v.is_deleted = FALSE
WHERE k.is_active = TRUE
GROUP BY k.key_name, k.total_requests, k.successful_requests, k.failed_requests, k.last_used_at
ORDER BY k.last_used_at DESC;

-- ============================================================================
-- Data Retention Policy (Cleanup old records)
-- ============================================================================

-- Function: Clean up old rate limit events (keep last 30 days)
CREATE OR REPLACE FUNCTION cleanup_old_rate_limit_events()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM rate_limit_events
    WHERE event_timestamp < NOW() - INTERVAL '30 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function: Archive old verification logs (soft delete after 1 year)
CREATE OR REPLACE FUNCTION archive_old_verification_logs()
RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER;
BEGIN
    UPDATE verification_logs
    SET is_deleted = TRUE, deleted_at = CURRENT_TIMESTAMP
    WHERE created_at < NOW() - INTERVAL '1 year'
    AND is_deleted = FALSE;
    
    GET DIAGNOSTICS archived_count = ROW_COUNT;
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Permissions
-- ============================================================================

-- Grant permissions to application user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO idv_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO idv_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO idv_user;

-- ============================================================================
-- Initial Data (Optional)
-- ============================================================================

-- Insert default admin API key (CHANGE IN PRODUCTION!)
-- This is just an example - generate real keys using the generate_secrets.sh script
INSERT INTO api_keys (key_name, key_hash, description, rate_limit_per_minute, metadata)
VALUES (
    'Admin Key (Example)',
    'CHANGE_ME_IN_PRODUCTION',
    'Default admin API key - MUST BE CHANGED',
    1000,
    '{"role": "admin", "permissions": ["all"]}'::jsonb
) ON CONFLICT DO NOTHING;

-- ============================================================================
-- Database Stats and Health Checks
-- ============================================================================

-- Create health check function
CREATE OR REPLACE FUNCTION health_check()
RETURNS TABLE (
    metric VARCHAR,
    value VARCHAR,
    status VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 'database_size'::VARCHAR, 
           pg_size_pretty(pg_database_size(current_database()))::VARCHAR,
           'ok'::VARCHAR
    UNION ALL
    SELECT 'connection_count'::VARCHAR,
           (SELECT count(*)::VARCHAR FROM pg_stat_activity),
           'ok'::VARCHAR
    UNION ALL
    SELECT 'table_count'::VARCHAR,
           (SELECT count(*)::VARCHAR FROM information_schema.tables WHERE table_schema = 'public'),
           'ok'::VARCHAR;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Completion Message
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Database initialization completed!';
    RAISE NOTICE 'Database: %', current_database();
    RAISE NOTICE 'Tables created: %', (SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public');
    RAISE NOTICE 'Indexes created: %', (SELECT count(*) FROM pg_indexes WHERE schemaname = 'public');
    RAISE NOTICE 'Timestamp: %', now();
    RAISE NOTICE '========================================';
END $$;
