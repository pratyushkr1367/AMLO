-- ─── Extensions ──────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS vector;

-- ─── Enums ───────────────────────────────────────────────────────────────────
CREATE TYPE machine_status AS ENUM ('NORMAL', 'DEGRADING', 'CRITICAL', 'OFFLINE');
CREATE TYPE technician_availability AS ENUM ('AVAILABLE', 'BUSY', 'OFF_SHIFT');
CREATE TYPE work_order_status AS ENUM ('OPEN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED');
CREATE TYPE work_order_priority AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');

-- ─── updated_at trigger ───────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ─── Machines ─────────────────────────────────────────────────────────────────
-- One row per physical asset on the factory floor.
-- location_row / location_col map to cells on the 50x50 AGV grid.
CREATE TABLE machines (
    id            SERIAL PRIMARY KEY,
    machine_id    VARCHAR(50)    UNIQUE NOT NULL,  -- e.g. "CNC-01"
    name          VARCHAR(100)   NOT NULL,
    type          VARCHAR(50)    NOT NULL,          -- e.g. "CNC", "Lathe", "Press"
    location_row  INT            NOT NULL,
    location_col  INT            NOT NULL,
    status        machine_status NOT NULL DEFAULT 'NORMAL',
    created_at    TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_machines_status   ON machines(status);
CREATE INDEX idx_machines_location ON machines(location_row, location_col);

CREATE TRIGGER trg_machines_updated_at
  BEFORE UPDATE ON machines
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ─── Technicians ──────────────────────────────────────────────────────────────
-- skills is a Postgres text array, e.g. '{"CNC","hydraulics","electrical"}'
CREATE TABLE technicians (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(100)             NOT NULL,
    skills        TEXT[]                   NOT NULL DEFAULT '{}',
    availability  technician_availability  NOT NULL DEFAULT 'AVAILABLE',
    location_row  INT                      NOT NULL DEFAULT 0,
    location_col  INT                      NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ              NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ              NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_technicians_availability ON technicians(availability);

CREATE TRIGGER trg_technicians_updated_at
  BEFORE UPDATE ON technicians
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ─── Inventory ────────────────────────────────────────────────────────────────
-- Spare parts stock. quantity = 0 triggers the Sourcing Agent to raise a PO.
CREATE TABLE inventory (
    id                 SERIAL PRIMARY KEY,
    part_number        VARCHAR(100)  UNIQUE NOT NULL,
    part_name          VARCHAR(200)  NOT NULL,
    quantity           INT           NOT NULL DEFAULT 0,
    unit               VARCHAR(20)   NOT NULL DEFAULT 'pcs',
    reorder_threshold  INT           NOT NULL DEFAULT 5,
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_inventory_quantity ON inventory(quantity);

CREATE TRIGGER trg_inventory_updated_at
  BEFORE UPDATE ON inventory
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ─── Work Orders ──────────────────────────────────────────────────────────────
-- Created by the Scheduling Agent once diagnosis + parts + technician are resolved.
-- parts_used  : [{"part_number": "PN-001", "qty": 2}, ...]
-- agv_route   : [{"row": 5, "col": 12}, {"row": 5, "col": 13}, ...]
CREATE TABLE work_orders (
    id             SERIAL PRIMARY KEY,
    machine_id     INT                  NOT NULL REFERENCES machines(id),
    technician_id  INT                  REFERENCES technicians(id),
    status         work_order_status    NOT NULL DEFAULT 'OPEN',
    priority       work_order_priority  NOT NULL DEFAULT 'MEDIUM',
    fault_type     VARCHAR(100),
    description    TEXT,
    parts_used     JSONB                NOT NULL DEFAULT '[]',
    agv_route      JSONB                NOT NULL DEFAULT '[]',
    created_at     TIMESTAMPTZ          NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ          NOT NULL DEFAULT NOW(),
    completed_at   TIMESTAMPTZ
);

CREATE INDEX idx_work_orders_status     ON work_orders(status);
CREATE INDEX idx_work_orders_machine    ON work_orders(machine_id);
CREATE INDEX idx_work_orders_technician ON work_orders(technician_id);
CREATE INDEX idx_work_orders_priority   ON work_orders(priority);

CREATE TRIGGER trg_work_orders_updated_at
  BEFORE UPDATE ON work_orders
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ─── Document Chunks (pgvector / RAG) ────────────────────────────────────────
-- Chunked machinery manuals embedded for semantic search.
-- embedding dimension: 1024 (Anthropic voyage-3 / voyage-3-lite)
CREATE TABLE document_chunks (
    id           SERIAL PRIMARY KEY,
    source_file  VARCHAR(255)  NOT NULL,
    chunk_index  INT           NOT NULL,
    content      TEXT          NOT NULL,
    embedding    vector(1024),
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (source_file, chunk_index)
);

CREATE INDEX idx_document_chunks_source    ON document_chunks(source_file);
-- HNSW index for sub-millisecond cosine similarity search
CREATE INDEX idx_document_chunks_embedding ON document_chunks
  USING hnsw (embedding vector_cosine_ops);

-- ─── Seed Data ───────────────────────────────────────────────────────────────
INSERT INTO machines (machine_id, name, type, location_row, location_col) VALUES
  ('CNC-01',   'CNC Machine 1',     'CNC',   5,  10),
  ('CNC-02',   'CNC Machine 2',     'CNC',   5,  20),
  ('LATHE-01', 'Lathe Machine 1',   'Lathe', 15, 10),
  ('LATHE-02', 'Lathe Machine 2',   'Lathe', 15, 25),
  ('PRESS-01', 'Hydraulic Press 1', 'Press', 25, 15),
  ('WELD-01',  'Welding Station 1', 'Welder',35, 10),
  ('WELD-02',  'Welding Station 2', 'Welder',35, 30);

INSERT INTO technicians (name, skills, location_row, location_col) VALUES
  ('Alice Chen',   ARRAY['CNC', 'electrical'],           0,  0),
  ('Bob Kumar',    ARRAY['hydraulics', 'Press'],          0, 49),
  ('Carol Smith',  ARRAY['CNC', 'Lathe', 'electrical'],  49,  0),
  ('David Osei',   ARRAY['Welder', 'electrical'],        49, 49),
  ('Eva Martinez', ARRAY['Lathe', 'hydraulics'],         25, 25);

INSERT INTO inventory (part_number, part_name, quantity, unit, reorder_threshold) VALUES
  ('PN-BELT-001', 'Drive Belt A40',        12, 'pcs',    3),
  ('PN-BEAR-002', 'Ball Bearing 6205',      8, 'pcs',    5),
  ('PN-FILT-003', 'Hydraulic Filter HF10',  2, 'pcs',    2),
  ('PN-SEAL-004', 'Oil Seal 40x60x10',      0, 'pcs',    4),
  ('PN-COOL-005', 'Coolant Fluid 5L',       6, 'liters', 2),
  ('PN-FUSE-006', 'Fuse 10A 250V',         20, 'pcs',   10),
  ('PN-CONT-007', 'Contactor LC1D09',       3, 'pcs',    2);
