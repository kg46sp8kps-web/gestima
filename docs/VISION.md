# GESTIMA Platform - Long-term Vision

**Status:** Draft v1.0
**Date:** 2026-01-26
**Horizon:** 1 year (Q1 2026 - Q1 2027)
**Target:** Full ERP/MES for in-house manufacturing
**Competitor benchmark:** Helios Inuvio (no integration planned)

---

## Mission Statement

Transform GESTIMA from CNC cost calculator into a complete manufacturing execution platform covering the full cycle: **Quote → Order → Production → Delivery**.

**Philosophy:**
- In-house only (no multi-tenancy)
- AI-accelerated development
- Modular architecture
- Zero integration with legacy systems

---

## Platform Architecture (Modular Domains)

```
GESTIMA Platform
│
├── 1. COSTING ✅ v1.4.0 (DONE)
│   ├── Materials (Groups + Items + Price Tiers)
│   ├── Machines (CRUD + hourly rate breakdown)
│   ├── Operations (turning, milling, grinding, coop)
│   ├── Features (geometric operations)
│   ├── Batches (1/10/100/500/1000 pricing)
│   └── Snapshots (frozen prices)
│
├── 2. QUOTES & ORDERS 📋 v2.0 (Q1 2026, ~3 weeks)
│   ├── Customers (B2B contacts, terms, payment conditions)
│   ├── Quotes (from frozen batches → PDF export)
│   ├── Quote Items (Part + quantity + delivery date)
│   ├── Quote Approval Workflow (draft → sent → approved)
│   ├── Orders (confirmed quotes → production trigger)
│   ├── Order Items (Part revision locking)
│   └── Delivery Management (packaging, shipping docs)
│
├── 3. PLM (Product Lifecycle) 📐 v3.0 (Q2 2026, ~4 weeks)
│   ├── Drawings (PDF/DXF storage, MinIO/S3-compatible)
│   ├── Drawing Versions (immutable, SHA-256 hash)
│   ├── Part Revisions (Part.revision A/B/C → Drawing.version)
│   ├── BOM (Bill of Materials, single-level first)
│   ├── ECN/ECO (Engineering Change Notifications/Orders)
│   ├── Approval Workflow (draft → review → approved → released)
│   └── Revision History (who changed what when)
│
├── 4. MES (Manufacturing Execution) 🏭 v4.0 (Q3 2026, ~6 weeks)
│   ├── Work Orders (výrobní příkazy from Orders)
│   ├── Routing (tech. postupy from Operations)
│   ├── Work Centers (machines + availability calendar)
│   ├── Job Scheduling (Gantt chart, capacity planning)
│   ├── Shop Floor Tracking (odvody práce - start/stop/pause)
│   ├── Tablets/Kiosks (paperless production for operators)
│   ├── Real-time Status (machine utilization, WIP tracking)
│   └── Downtime Tracking (breakdowns, maintenance)
│
├── 5. TECHNOLOGY DATABASE 🔧 v5.0 (Q4 2026, ~4 weeks)
│   ├── Materials CRUD (advanced mgmt beyond price tiers)
│   ├── Cutting Conditions CRUD (feeds, speeds, DOC)
│   ├── Tool Library (inserts, holders, presets)
│   ├── Technology Sheets (recommended params per material)
│   ├── Machine Capabilities (spindle power, torque, rpm)
│   └── Analytics (machine utilization, cost per hour actual vs planned)
│
└── 6. FUTURE MODULES 🚀 v6.0+ (2027+)
    ├── Warehouse (inventory, stock movements, min/max)
    ├── QA (inspection plans, measurements, NCR)
    ├── Reporting & BI (OEE, dashboards, analytics)
    ├── Maintenance (preventive, work orders for machines)
    └── Multi-level BOM (assemblies, sub-assemblies)
```

---

## Roadmap with Effort Estimates (AI-accelerated)

### Q1 2026: Quotes & Orders (v2.0)

**Duration:** 3 weeks | **Modules:** 2

| Task | Effort | Priority |
|------|--------|----------|
| Customer model (name, contact, terms) | 2h | HIGH |
| Quote model (status workflow) | 3h | HIGH |
| Quote Items (Part FK, quantity, price snapshot) | 2h | HIGH |
| Quote → PDF export (invoice-like layout) | 4h | HIGH |
| Order model (from approved Quote) | 3h | HIGH |
| Order Items (revision locking) | 2h | HIGH |
| Quote/Order UI (list, create, edit) | 8h | HIGH |
| Email notifications (quote sent, order confirmed) | 3h | MEDIUM |
| Quote approval workflow | 2h | MEDIUM |
| **TOTAL** | **29h** (~3 weeks) | |

**Key Features:**
- Quote sends → customer email
- Approved quote → Order (1-click conversion)
- Order locks Part.revision (immutable reference)
- Delivery date tracking

---

### Q2 2026: PLM & Drawings (v3.0)

**Duration:** 4 weeks | **Modules:** 1

| Task | Effort | Priority |
|------|--------|----------|
| MinIO/S3 setup (local storage layer) | 3h | HIGH |
| Drawing model (file storage, hash, metadata) | 3h | HIGH |
| Drawing Versions (immutable, parent-child chain) | 4h | HIGH |
| Part.revision field (A/B/C naming) | 2h | HIGH |
| Upload UI (drag-drop, preview for PDFs) | 6h | HIGH |
| Viewer integration (PDF.js for browser view) | 4h | HIGH |
| BOM model (single-level, Part → Components) | 4h | MEDIUM |
| BOM UI (tree view, add/remove components) | 6h | MEDIUM |
| ECN/ECO workflow (change request → approval) | 5h | MEDIUM |
| Drawing approval workflow (draft → review → released) | 4h | MEDIUM |
| Revision history timeline | 3h | LOW |
| **TOTAL** | **44h** (~4 weeks) | |

**Key Features:**
- PDF/DXF upload with version control
- SHA-256 hash for duplicate detection
- Part.revision synced with Drawing.version
- ECN → triggers new revision automatically
- Approval workflow (3 states: draft, review, released)

---

### Q3 2026: MES & Work Orders (v4.0)

**Duration:** 6 weeks | **Modules:** 1

| Task | Effort | Priority |
|------|--------|----------|
| WorkOrder model (from Order, status FSM) | 4h | HIGH |
| WorkOrder Items (Operation → task assignments) | 3h | HIGH |
| Work Center model (Machine + calendar availability) | 3h | HIGH |
| Job Scheduling API (basic FIFO, no optimization yet) | 6h | HIGH |
| Shop Floor Tracking (start/stop/pause buttons) | 5h | HIGH |
| Tablet/Kiosk UI (operator-friendly, big buttons) | 8h | HIGH |
| QR code generation (WorkOrder → scannable) | 3h | MEDIUM |
| Real-time status updates (WebSocket or polling) | 5h | MEDIUM |
| Downtime tracking (reason codes, duration) | 4h | MEDIUM |
| Machine utilization dashboard | 6h | MEDIUM |
| Gantt chart (scheduling visualization) | 8h | LOW |
| Capacity planning (load analysis) | 6h | LOW |
| **TOTAL** | **61h** (~6 weeks) | |

**Key Features:**
- Order → WorkOrder (1:N, multiple WOs per Order)
- Operator logs: start job → complete operation → finish job
- Tablet UI: QR scan → show WorkOrder → log time
- Real-time tracking: who's working on what machine
- Downtime reasons: breakdown, no material, waiting for QA, etc.

---

### Q4 2026: Technology Database (v5.0)

**Duration:** 4 weeks | **Modules:** 1

| Task | Effort | Priority |
|------|--------|----------|
| Materials CRUD UI (full management beyond price) | 4h | HIGH |
| Cutting Conditions CRUD UI | 4h | HIGH |
| Tool Library model (inserts, holders, assemblies) | 4h | MEDIUM |
| Technology Sheets (recommended params per material/operation) | 5h | MEDIUM |
| Machine Capabilities (spindle, torque, rpm ranges) | 3h | MEDIUM |
| Feed/Speed calculator (from cutting conditions) | 4h | MEDIUM |
| Analytics: machine utilization actual vs planned | 6h | LOW |
| Tool wear tracking (usage hours, replacement alerts) | 5h | LOW |
| **TOTAL** | **35h** (~4 weeks) | |

**Key Features:**
- Editable Materials (not just seed data)
- Editable Cutting Conditions (admin control)
- Tool catalog (for future tool management)
- Technology recommendations (best practices per material)
- Machine capability checks (can this machine do this operation?)

---

## Critical Architectural Decisions

### VIS-001: Soft Delete Everywhere
**Date:** 2026-01-26
**Decision:** ALL models MUST use soft delete (deleted_at field)
**Reason:** Orders/WorkOrders need stable FK references to Parts/Operations even after "deletion"
**Impact:** Future modules rely on historical data integrity
**Implementation:** Use `AuditMixin` pattern (already in v1.4)

### VIS-002: Immutable Snapshots
**Date:** 2026-01-26
**Decision:** When locking references (Quote, Order, WorkOrder), copy data as JSON snapshot
**Reason:** Price changes, material updates, machine rate changes must NOT affect historical records
**Pattern:**
```python
Order.part_snapshot = {
    "part_id": 123,
    "part_number": "PN-001",
    "material": "Stainless 316L",
    "price_per_unit": 45.67,
    "batch_quantity": 100,
    "snapshot_date": "2026-01-26T10:00:00Z"
}
```
**Impact:** Quotes/Orders are audit-proof, reproducible calculations

### VIS-003: Version Tracking Everywhere
**Date:** 2026-01-26
**Decision:** All entities with potential concurrent edits MUST have `version` field (optimistic locking)
**Reason:** Multi-user editing (operator updating WorkOrder while admin changes Part)
**Implementation:** Already in Part, Batch → extend to Order, WorkOrder, Drawing
**Pattern:** ADR-008 (existing)

### VIS-004: API Versioning
**Date:** 2026-01-26
**Decision:** Major API changes require version bump (`/api/v1/`, `/api/v2/`)
**Reason:** Frontend/Mobile apps need stability
**Trigger:** Breaking schema changes (remove field, rename, change type)
**Non-breaking:** Add optional field, new endpoint → same version OK

### VIS-005: Background Jobs (Future)
**Date:** 2026-01-26
**Decision:** Long-running tasks (PDF generation, reports, scheduling) → background jobs
**Tech:** Celery + Redis (when needed, not v1.x-v2.x)
**Trigger:** Any operation >5s response time
**Priority:** LOW (wait for actual need)

### VIS-006: File Storage Strategy
**Date:** 2026-01-26
**Decision:** MinIO for file storage (S3-compatible, self-hosted)
**Reason:** PDF/DXF drawings, future photos/scans
**Structure:** `/drawings/{part_id}/{revision}/{hash}.pdf`
**Backup:** MinIO sync to external drive (separate from DB backups)

### VIS-007: Single Database (No Microservices)
**Date:** 2026-01-26
**Decision:** Monolithic app, single DB, modular code (NOT microservices)
**Reason:** In-house only, <100 users, simpler ops
**Migration path:** If >500 users, consider PostgreSQL + read replicas (NOT service split)
**Trade-off:** Simplicity > scalability (acceptable for 1-year horizon)

---

## Integration Points (Cross-Module Dependencies)

### Quotes → Orders
```
Quote.status = "approved"
  → Button: "Create Order"
  → Order.quote_id FK
  → Order.items = copy(Quote.items)
  → Order.part_snapshot = freeze current Part state
```

### Orders → Work Orders
```
Order.status = "confirmed"
  → Button: "Generate Work Orders"
  → WorkOrder.order_id FK
  → WorkOrder.items = copy(Order.items.operations)
  → Routing = sequence of WorkOrder.items
```

### Parts → Drawings
```
Part.drawing_id FK (nullable, optional)
Part.revision = "A" (default, editable)
Drawing.version = 1, 2, 3... (immutable)
ECN triggered → Part.revision++, Drawing.version++
```

### Machines → Work Centers
```
Machine (v1.4) = master data (cost, capabilities)
WorkCenter (v4.0) = Machine + calendar + real-time status
WorkCenter.machine_id FK → Machine
WorkCenter.status = "idle" | "busy" | "down" | "maintenance"
```

### Materials → Technology
```
MaterialGroup/Item (v1.4) = pricing
Material (v5.0) = full properties (hardness, machinability, density)
CuttingConditions (v1.4) = read-only seed data
CuttingConditions (v5.0) = editable admin UI
Technology Sheet = MaterialItem × Operation → recommended params
```

---

## Migration Strategy (SQLite → PostgreSQL)

### v1.x - v3.x: SQLite (Current)
- **Reason:** Rapid prototyping, simple ops, <10 users
- **Limits:** Single writer, no full-text search, limited concurrent writes
- **Acceptable:** Dev + small pilot deployment

### v4.x: PostgreSQL Evaluation
- **Trigger:** >10 concurrent users OR real-time MES requirements
- **Benefits:** Row-level locking, full-text search, JSON operators, better concurrency
- **Effort:** ~1 week (schema migration, test, deploy)
- **Decision point:** Q3 2026 based on pilot feedback

### v5.x+: PostgreSQL + Read Replicas (Optional)
- **Trigger:** >50 users OR heavy analytics/reporting load
- **Pattern:** Write to primary, read from replica (dashboards, reports)
- **Effort:** ~3 days (replication setup, connection pool config)

---

## Monitoring & Success Metrics

### v2.0 (Quotes & Orders)
- **Metric:** Quote → Order conversion rate >60%
- **Metric:** Quote generation time <2 minutes
- **Metric:** PDF export time <5 seconds

### v3.0 (PLM)
- **Metric:** Drawing upload time <10 seconds for 5MB PDF
- **Metric:** Revision approval cycle <24 hours
- **Metric:** Zero duplicate file storage (hash dedup working)

### v4.0 (MES)
- **Metric:** WorkOrder completion tracking >90% accuracy
- **Metric:** Operator login time <30 seconds (tablet UX)
- **Metric:** Real-time status update latency <2 seconds
- **Metric:** Machine utilization calculation error <5%

### v5.0 (Technology)
- **Metric:** Technology sheet lookup time <500ms
- **Metric:** Admin CRUD response time <1 second
- **Metric:** Feed/speed calculator accuracy ±10% vs manual calculation

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| SQLite concurrency limits hit early | MEDIUM | HIGH | Early PostgreSQL migration (Q2 instead of Q3) |
| File storage grows >100GB | LOW | MEDIUM | MinIO quotas, old drawing archival |
| Operator tablet adoption resistance | MEDIUM | HIGH | UX testing with real operators, training sessions |
| Drawings without version control (legacy) | HIGH | LOW | Import tool: auto-version existing PDFs as v1 |
| Real-time MES tracking latency >5s | LOW | HIGH | WebSocket optimization, edge caching |

---

## Development Principles (Roy's Way)

✅ **DO:**
- Plan before implement (architecture discussion first)
- Write tests for business logic (calc, workflows)
- Use Pydantic validation everywhere
- Document arch decisions (ADR for each breaking change)
- Soft delete all entities
- Snapshot data when locking references
- Version all concurrent-edit entities

❌ **DON'T:**
- Over-engineer (KISS principle)
- Add features "just in case"
- Skip error handling (try/except MUST cover DB ops)
- Hardcode values (always DB/config)
- Breaking changes without version bump
- Delete data (soft delete only)
- Compute values on-the-fly when snapshot should be used

---

## Open Questions (To Be Decided)

1. **Email service:** SendGrid/AWS SES vs self-hosted SMTP? → Decide in v2.0
2. **Mobile app:** Native (React Native) vs PWA? → Decide in v4.0 based on tablet pilot
3. **Barcode scanning:** QR only or support Code128/DataMatrix? → Decide in v4.0
4. **Multi-language:** Czech only or add English/German? → Decide in v5.0 based on demand
5. **Backups:** Current daily CLI backup vs continuous replication? → Decide at PostgreSQL migration

---

## Version History

- **v1.0** (2026-01-26): Initial vision document, 1-year roadmap, 5 modules prioritized

---

**Next Review:** Q2 2026 (after v2.0 Quotes/Orders deployment)
**Owner:** Development Team
**Status:** DRAFT (pending approval)
