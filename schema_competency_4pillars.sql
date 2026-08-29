-- 1. Table for Target Benchmarks per Designation across 4 Pillars
CREATE TABLE IF NOT EXISTS designation_competency_targets (
    designation_name VARCHAR(150) PRIMARY KEY,
    cadre_name VARCHAR(100) NOT NULL,
    target_statistical INTEGER NOT NULL DEFAULT 85,
    target_technical INTEGER NOT NULL DEFAULT 85,
    target_governance INTEGER NOT NULL DEFAULT 80,
    target_behavioural INTEGER NOT NULL DEFAULT 80
);

-- 2. Table for Individual Officer Data (Stored per employee)
CREATE TABLE IF NOT EXISTS officer_profiles (
    officer_id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    department VARCHAR(150) NOT NULL,
    designation_name VARCHAR(150) REFERENCES designation_competency_targets(designation_name),
    current_statistical INTEGER DEFAULT 0,
    current_technical INTEGER DEFAULT 0,
    current_governance INTEGER DEFAULT 0,
    current_behavioural INTEGER DEFAULT 0,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Seed Target Standards for Designations
INSERT INTO designation_competency_targets 
(designation_name, cadre_name, target_statistical, target_technical, target_governance, target_behavioural)
VALUES
('Director General (DG / Apex Level) - ISS', 'Indian Statistical Service (ISS)', 95, 85, 98, 95),
('Additional Director General (ADG / HAG) - ISS', 'Indian Statistical Service (ISS)', 94, 85, 95, 92),
('Deputy Director General (DDG / SAG) - ISS', 'Indian Statistical Service (ISS)', 92, 88, 92, 90),
('Director / Joint Director (JAG) - ISS', 'Indian Statistical Service (ISS)', 92, 90, 88, 85),
('Deputy Director (STS) - ISS', 'Indian Statistical Service (ISS)', 90, 92, 85, 82),
('Assistant Director (JTS) - ISS', 'Indian Statistical Service (ISS)', 90, 90, 85, 80),
('Probationer / Officer Trainee (ISS - NSSTA)', 'Indian Statistical Service (ISS)', 88, 88, 82, 80),
('Senior Statistical Officer (SSO / Gazetted)', 'Subordinate Statistical Service (SSS)', 88, 85, 82, 80),
('Senior Statistical Officer (SSO / Non-Gazetted)', 'Subordinate Statistical Service (SSS)', 85, 82, 80, 78),
('Junior Statistical Officer (JSO)', 'Subordinate Statistical Service (SSS)', 82, 82, 78, 75),
('Statistical Assistant / Senior Field Investigator', 'Subordinate Statistical Service (SSS)', 80, 78, 75, 75),
('Director of Economics & Statistics (State Head)', 'State DES Statistical Cadre', 92, 85, 95, 92),
('Joint / Deputy Director (State DES)', 'State DES Statistical Cadre', 90, 85, 88, 85),
('District Statistical Officer (DSO)', 'State DES Statistical Cadre', 85, 82, 82, 82),
('Assistant Statistical Officer / Statistical Officer (State)', 'State DES Statistical Cadre', 82, 80, 78, 75),
('Statistical Inspector / Research Assistant (DES)', 'State DES Statistical Cadre', 80, 78, 75, 75),
('Primary Field Investigator / Enumerator', 'State DES Statistical Cadre', 78, 75, 72, 75)
ON CONFLICT (designation_name) DO UPDATE SET
    target_statistical = EXCLUDED.target_statistical,
    target_technical = EXCLUDED.target_technical,
    target_governance = EXCLUDED.target_governance,
    target_behavioural = EXCLUDED.target_behavioural;

-- 4. Individual Officer Level Gap Analysis View (Row per Officer)
CREATE OR REPLACE VIEW officer_individual_competency_view AS
SELECT 
    o.officer_id,
    o.full_name,
    o.email,
    o.department,
    o.designation_name,
    t.cadre_name,
    t.target_statistical AS needed_statistical,
    o.current_statistical AS current_statistical,
    GREATEST(0, t.target_statistical - o.current_statistical) AS gap_to_learn_statistical,
    t.target_technical AS needed_technical,
    o.current_technical AS current_technical,
    GREATEST(0, t.target_technical - o.current_technical) AS gap_to_learn_technical,
    t.target_governance AS needed_governance,
    o.current_governance AS current_governance,
    GREATEST(0, t.target_governance - o.current_governance) AS gap_to_learn_governance,
    t.target_behavioural AS needed_behavioural,
    o.current_behavioural AS current_behavioural,
    GREATEST(0, t.target_behavioural - o.current_behavioural) AS gap_to_learn_behavioural
FROM officer_profiles o
JOIN designation_competency_targets t ON o.designation_name = t.designation_name;

-- 5. Admin Aggregated View (Grouped by Designation)
CREATE OR REPLACE VIEW admin_designation_competency_summary AS
SELECT 
    t.designation_name,
    t.cadre_name,
    COUNT(o.officer_id) AS total_officers_enrolled,
    t.target_statistical AS needed_statistical,
    ROUND(COALESCE(AVG(o.current_statistical), 0), 2) AS avg_current_statistical,
    ROUND(GREATEST(0, t.target_statistical - COALESCE(AVG(o.current_statistical), 0)), 2) AS avg_gap_to_learn_statistical,
    t.target_technical AS needed_technical,
    ROUND(COALESCE(AVG(o.current_technical), 0), 2) AS avg_current_technical,
    ROUND(GREATEST(0, t.target_technical - COALESCE(AVG(o.current_technical), 0)), 2) AS avg_gap_to_learn_technical,
    t.target_governance AS needed_governance,
    ROUND(COALESCE(AVG(o.current_governance), 0), 2) AS avg_current_governance,
    ROUND(GREATEST(0, t.target_governance - COALESCE(AVG(o.current_governance), 0)), 2) AS avg_gap_to_learn_governance,
    t.target_behavioural AS needed_behavioural,
    ROUND(COALESCE(AVG(o.current_behavioural), 0), 2) AS avg_current_behavioural,
    ROUND(GREATEST(0, t.target_behavioural - COALESCE(AVG(o.current_behavioural), 0)), 2) AS avg_gap_to_learn_behavioural
FROM designation_competency_targets t
LEFT JOIN officer_profiles o ON t.designation_name = o.designation_name
GROUP BY 
    t.designation_name, 
    t.cadre_name, 
    t.target_statistical, 
    t.target_technical, 
    t.target_governance, 
    t.target_behavioural;