-- Tables for visualization (simplified schema)
CREATE TABLE vcns (
  id VARCHAR2(64) PRIMARY KEY,
  display_name VARCHAR2(255),
  compartment_id VARCHAR2(64),
  cidr_block VARCHAR2(64)
);

CREATE TABLE subnets (
  id VARCHAR2(64) PRIMARY KEY,
  display_name VARCHAR2(255),
  compartment_id VARCHAR2(64),
  vcn_id VARCHAR2(64),
  cidr_block VARCHAR2(64)
);

CREATE TABLE instances (
  id VARCHAR2(64) PRIMARY KEY,
  display_name VARCHAR2(255),
  compartment_id VARCHAR2(64),
  shape VARCHAR2(128),
  lifecycle_state VARCHAR2(64),
  availability_domain VARCHAR2(64)
);

CREATE TABLE load_balancers (
  id VARCHAR2(64) PRIMARY KEY,
  display_name VARCHAR2(255),
  compartment_id VARCHAR2(64),
  shape VARCHAR2(128)
);

CREATE TABLE functions_apps (
  id VARCHAR2(64) PRIMARY KEY,
  display_name VARCHAR2(255),
  compartment_id VARCHAR2(64)
);

CREATE TABLE streams (
  id VARCHAR2(64) PRIMARY KEY,
  name VARCHAR2(255),
  compartment_id VARCHAR2(64)
);

CREATE TABLE costs_summary (
  as_of TIMESTAMP,
  total_cost NUMBER,
  currency VARCHAR2(16)
);

CREATE TABLE capacity_report (
  as_of TIMESTAMP,
  compartment_id VARCHAR2(64),
  total_instances NUMBER,
  running_instances NUMBER,
  stopped_instances NUMBER,
  shapes_used NUMBER
);

