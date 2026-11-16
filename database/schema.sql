-- =====================================================================
-- WorkflowGuard: Process Workflow Anomaly Detection System
-- Database Schema for MySQL 8.0+
-- =====================================================================

CREATE DATABASE IF NOT EXISTS workflowguard_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE workflowguard_db;

-- ---------------------------------------------------------------------
-- 1. Table: workflows
-- Defines registered business process workflows
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS workflows (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE COMMENT 'Unique machine key (e.g., PAYMENT_PROCESSING)',
    name VARCHAR(100) NOT NULL COMMENT 'Display name of the workflow',
    description TEXT NULL COMMENT 'Detailed workflow purpose and semantics',
    version INT NOT NULL DEFAULT 1 COMMENT 'Schema version for workflow evolution',
    is_active BOOLEAN NOT NULL DEFAULT TRUE COMMENT 'Whether the workflow is enabled',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 2. Table: workflow_states
-- Set of formal states Q in the DFA for a given workflow
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS workflow_states (
    id INT AUTO_INCREMENT PRIMARY KEY,
    workflow_id INT NOT NULL,
    state_key VARCHAR(50) NOT NULL COMMENT 'Unique identifier in workflow (e.g. ORDER_CREATED)',
    state_name VARCHAR(100) NOT NULL COMMENT 'Human-readable state label',
    state_type ENUM('START', 'INTERMEDIATE', 'TERMINAL_SUCCESS', 'TERMINAL_FAILURE', 'ERROR') NOT NULL,
    description VARCHAR(255) NULL,
    is_initial BOOLEAN NOT NULL DEFAULT FALSE,
    is_terminal BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_workflow_state UNIQUE (workflow_id, state_key),
    CONSTRAINT fk_state_workflow FOREIGN KEY (workflow_id)
        REFERENCES workflows(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 3. Table: workflow_transitions
-- Allowed transition function delta(q, a) = p for DFA verification
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS workflow_transitions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    workflow_id INT NOT NULL,
    from_state_id INT NOT NULL,
    to_state_id INT NOT NULL,
    event_name VARCHAR(50) NOT NULL COMMENT 'Input symbol in alphabet Sigma (e.g. INITIATE_PAYMENT)',
    is_allowed BOOLEAN NOT NULL DEFAULT TRUE COMMENT 'Whether the transition is structurally valid',
    max_retries INT NOT NULL DEFAULT 0 COMMENT 'Max retry attempts allowed from this state',
    condition_meta JSON NULL COMMENT 'Guard conditions (e.g., {"retry_limit": 3})',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_state_event UNIQUE (workflow_id, from_state_id, event_name),
    CONSTRAINT fk_transition_workflow FOREIGN KEY (workflow_id)
        REFERENCES workflows(id) ON DELETE CASCADE,
    CONSTRAINT fk_transition_from_state FOREIGN KEY (from_state_id)
        REFERENCES workflow_states(id) ON DELETE CASCADE,
    CONSTRAINT fk_transition_to_state FOREIGN KEY (to_state_id)
        REFERENCES workflow_states(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 4. Table: process_cases
-- Active or completed business instances/traces
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS process_cases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL UNIQUE COMMENT 'Unique business identifier (UUID or Case ID)',
    workflow_id INT NOT NULL,
    current_state_id INT NOT NULL,
    status ENUM('RUNNING', 'COMPLETED', 'FAILED', 'ANOMALOUS') NOT NULL DEFAULT 'RUNNING',
    total_amount DECIMAL(12, 2) NULL COMMENT 'Monetary value for payment workflows',
    user_id VARCHAR(64) NULL COMMENT 'Initiator/actor identifier',
    retry_count INT NOT NULL DEFAULT 0 COMMENT 'Current count of payment retries executed',
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    metadata_json JSON NULL COMMENT 'Extensible runtime metadata',
    CONSTRAINT fk_case_workflow FOREIGN KEY (workflow_id)
        REFERENCES workflows(id) ON DELETE RESTRICT,
    CONSTRAINT fk_case_current_state FOREIGN KEY (current_state_id)
        REFERENCES workflow_states(id) ON DELETE RESTRICT,
    INDEX idx_cases_status (status),
    INDEX idx_cases_started_at (started_at)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 5. Table: event_logs
-- Immutable sequence of executed process steps (Input trace w)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS event_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL,
    workflow_id INT NOT NULL,
    event_name VARCHAR(50) NOT NULL COMMENT 'Event input symbol triggered',
    from_state_key VARCHAR(50) NOT NULL COMMENT 'State before event trigger',
    to_state_key VARCHAR(50) NOT NULL COMMENT 'State after event execution',
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    execution_duration_ms INT NOT NULL DEFAULT 0 COMMENT 'Duration in milliseconds',
    retry_count INT NOT NULL DEFAULT 0 COMMENT 'Retry attempt index',
    payload_json JSON NULL COMMENT 'Contextual payload for ML feature extraction',
    CONSTRAINT fk_event_case FOREIGN KEY (case_id)
        REFERENCES process_cases(case_id) ON DELETE CASCADE,
    CONSTRAINT fk_event_workflow FOREIGN KEY (workflow_id)
        REFERENCES workflows(id) ON DELETE CASCADE,
    INDEX idx_event_case_time (case_id, timestamp),
    INDEX idx_event_name (event_name)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 6. Table: anomaly_results
-- Detection verdicts generated by DFA, Isolation Forest, and Hybrid Engine
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS anomaly_results (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL,
    event_log_id BIGINT NULL COMMENT 'Specific event causing violation, if applicable',
    detector_type ENUM('DFA', 'ISOLATION_FOREST', 'HYBRID') NOT NULL,
    is_anomaly BOOLEAN NOT NULL DEFAULT FALSE,
    anomaly_score FLOAT NULL COMMENT 'Continuous score (e.g. IF anomaly score or decision weight)',
    anomaly_reason VARCHAR(255) NOT NULL COMMENT 'Readable violation or anomaly rationale',
    severity ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') NOT NULL,
    rule_violation VARCHAR(100) NULL COMMENT 'DFA rule violated, e.g. ILLEGAL_TRANSITION',
    detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    details_json JSON NULL COMMENT 'Feature vector, decision metrics, and attribution',
    CONSTRAINT fk_anomaly_case FOREIGN KEY (case_id)
        REFERENCES process_cases(case_id) ON DELETE CASCADE,
    CONSTRAINT fk_anomaly_event FOREIGN KEY (event_log_id)
        REFERENCES event_logs(id) ON DELETE CASCADE,
    INDEX idx_anomaly_case (case_id),
    INDEX idx_anomaly_severity (severity)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- SEED DATA: Online Payment Processing Workflow
-- ---------------------------------------------------------------------
INSERT INTO workflows (id, code, name, description, version, is_active)
VALUES (
    1,
    'ONLINE_PAYMENT',
    'Online Payment Processing Workflow',
    'Standard e-commerce checkout flow containing order creation, payment attempt, verification, retries, and resolution.',
    1,
    TRUE
) ON DUPLICATE KEY UPDATE name=VALUES(name);

-- Workflow States (Q)
INSERT INTO workflow_states (id, workflow_id, state_key, state_name, state_type, description, is_initial, is_terminal)
VALUES
    (1, 1, 'ORDER_CREATED', 'Order Created', 'START', 'Initial state upon checkout session establishment', TRUE, FALSE),
    (2, 1, 'PAYMENT_INITIATED', 'Payment Initiated', 'INTERMEDIATE', 'Customer initiated payment gateway handoff', FALSE, FALSE),
    (3, 1, 'PAYMENT_VERIFYING', 'Payment Verifying', 'INTERMEDIATE', 'Asynchronous verification with payment processor', FALSE, FALSE),
    (4, 1, 'PAYMENT_FAILED', 'Payment Failed', 'INTERMEDIATE', 'Payment attempt was declined or timed out', FALSE, FALSE),
    (5, 1, 'ORDER_CONFIRMED', 'Order Confirmed', 'TERMINAL_SUCCESS', 'Payment successfully settled; order finalized', FALSE, TRUE),
    (6, 1, 'ORDER_CANCELLED', 'Order Cancelled', 'TERMINAL_FAILURE', 'Order aborted by user or exceeded retry exhaustion', FALSE, TRUE),
    (7, 1, 'TRAP_STATE', 'Trap / Reject State', 'ERROR', 'Dead-end DFA state entered upon illegal transition', FALSE, TRUE)
ON DUPLICATE KEY UPDATE state_name=VALUES(state_name);

-- Workflow Allowed Transitions (delta)
-- Max retries configured as 3 for PAYMENT_FAILED -> PAYMENT_INITIATED
INSERT INTO workflow_transitions (workflow_id, from_state_id, to_state_id, event_name, is_allowed, max_retries, condition_meta)
VALUES
    (1, 1, 2, 'INITIATE_PAYMENT', TRUE, 0, NULL),
    (1, 1, 6, 'CANCEL_ORDER', TRUE, 0, NULL),
    (1, 2, 3, 'VERIFY_PAYMENT', TRUE, 0, NULL),
    (1, 2, 6, 'CANCEL_ORDER', TRUE, 0, NULL),
    (1, 3, 5, 'PAYMENT_SUCCESS', TRUE, 0, NULL),
    (1, 3, 4, 'PAYMENT_FAILURE', TRUE, 0, NULL),
    (1, 4, 2, 'RETRY_PAYMENT', TRUE, 3, JSON_OBJECT('max_retries', 3, 'rule', 'retry_count < 3')),
    (1, 4, 6, 'EXCEED_MAX_RETRIES', TRUE, 3, JSON_OBJECT('rule', 'retry_count >= 3')),
    (1, 4, 6, 'CANCEL_ORDER', TRUE, 0, NULL)
ON DUPLICATE KEY UPDATE is_allowed=VALUES(is_allowed);
