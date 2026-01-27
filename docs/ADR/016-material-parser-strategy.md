# ADR-016: Material Parser Strategy (3-Phase Approach)

**Date:** 2026-01-27
**Status:** IMPLEMENTED (Fáze 1)
**Decision:** Implementovat 3-fázový search system: Regex → Fuzzy → AI
**Scope:** Materials, future search across all modules

---

## Context

Uživatelé často znají materiál ve zkráceném formátu typu:
- "D20 C45 100mm" (kulatina průměr 20, ocel C45, délka 100)
- "20x30 1.4301 500" (profil 20x30, nerez, délka 500)
- "t2 S235" (plech 2mm, ocel S235)

Manuální výběr přes dropdowny (stock_shape → category → dimensions) je pomalý a náchylný k chybám.

**Cíl:** Umožnit rychlé zadání materiálu přes jednoduchý textový input s automatickým rozpoznáním.

**Broader Vision:** Vytvořit reusable search infrastructure pro budoucí moduly (Quotes, PLM, MES, Tech DB).

---

## Decision

Implementovat **3-fázový search system**:

### **Fáze 1: Regex Parser (v1.4 - DONE)**
- **Tech:** Python regex patterns
- **Scope:** Materials only
- **Capabilities:**
  - Shape detection: D20, 20x30, □30, ⬡24, t2, D20x2
  - Material norm: 1.4301, C45, S235, EN AW-6060, CuZn37, atd.
  - Length extraction: 100mm, L=100, length=100
  - DB lookup: MaterialNorm → MaterialGroup → PriceCategory
- **Limitations:**
  - No typo tolerance (C54 ≠ C45)
  - No fuzzy matching
  - No semantic search
- **Effort:** 12h (COMPLETED)

### **Fáze 2: Generic Fuzzy Search (v2.5 - Q2 2026)**
- **Tech:** Meilisearch (self-hosted, typo-tolerant)
- **Scope:** All modules (Parts, Quotes, PLM, Orders, WorkOrders)
- **Capabilities:**
  - Typo tolerance ("neresz" → "nerez")
  - Partial match ("1.43" → "1.4301")
  - Multi-entity search (search across Parts, Customers, Drawings)
  - Fast autocomplete (< 50ms)
- **Trigger:** >3 modules need search functionality
- **Effort:** ~12h (Meilisearch setup + integration)

### **Fáze 3: AI Semantic Search (v5.0+ - Q4 2026)**
- **Tech:** Sentence Transformers (open-source) + Qdrant (vector DB)
- **Scope:** Tech DB primarily (complex queries)
- **Capabilities:**
  - Semantic queries: "nástroj pro tvrdý materiál nad 250HB s vysokým posuvem"
  - Similarity search: "najdi podobné díly jako PN-12345"
  - Context-aware recommendations
- **Trigger:** Real user feedback that fuzzy search není dostačující
- **Effort:** ~40h (ML pipeline, embeddings, vector DB)

---

## Fáze 1 Implementation Details

### **Backend Service**

```python
# app/services/material_parser.py

class MaterialParserService:
    """
    Regex-based parser pro materiálové popisy.

    Podporované formáty:
    - D20 1.4301 100mm (kulatina)
    - 20x20 C45 500 (čtyřhran)
    - 20x30 S235 500 (profil)
    - t2 1.4301 (plech)
    - D20x2 1.4301 100 (trubka)
    - ⬡24 CuZn37 150 (šestihran)
    """

    async def parse(self, description: str) -> ParseResult:
        """
        Hlavní parsing funkce.

        Výstup:
        - shape: StockShape (round_bar, square_bar, ...)
        - dimensions: diameter, width, height, thickness, wall_thickness
        - material_norm: "C45", "1.4301", "S235"
        - material_category: "ocel", "nerez", "hlinik" (fallback)
        - length: mm
        - confidence: 0.0-1.0
        - suggested_*: DB lookup results
        """
```

**Confidence Scoring:**
- Shape detected: +0.4
- Material norm detected: +0.3
- Length detected: +0.1
- MaterialGroup found in DB: +0.1
- PriceCategory found in DB: +0.05
- MaterialItem found in DB: +0.05

**Maximální confidence:** 1.0 (full match s DB lookup)

### **API Endpoint**

```python
POST /api/materials/parse?description=D20+C45+100mm

Response: ParseResult {
  "raw_input": "D20 C45 100mm",
  "shape": "round_bar",
  "diameter": 20.0,
  "length": 100.0,
  "material_norm": "C45",
  "material_category": "ocel",
  "suggested_material_group_id": 3,
  "suggested_material_group_code": "C45",
  "suggested_material_group_density": 7.85,
  "suggested_price_category_id": 5,
  "confidence": 0.95,
  "matched_pattern": "round_bar"
}
```

### **Frontend Component (Alpine.js)**

```html
<!-- parts/edit.html - Material ribbon -->
<div class="quick-material-input">
  <input
    type="text"
    x-model="quickMaterialInput"
    @input="debouncedParseMaterial()"
    placeholder="D20 C45 100mm..."
  >

  <!-- Parse result preview -->
  <div x-show="parseResult && parseResult.confidence > 0">
    <span x-show="parseResult.confidence >= 0.7">✅ ROZPOZNÁNO</span>
    <span x-show="parseResult.confidence < 0.7">⚠️ ČÁSTEČNĚ</span>

    <!-- Recognized values -->
    <div>
      Tvar: <span x-text="formatShape(parseResult.shape)"></span>
      Materiál: <span x-text="parseResult.suggested_material_group_name"></span>
      ...
    </div>

    <button @click="applyParsedMaterial()">Použít</button>
    <button @click="clearParseResult()">Zrušit</button>
  </div>
</div>
```

**UX Flow:**
1. User types "D20 C45 100mm"
2. Debounced parse (500ms)
3. Show confidence + recognized values
4. Click "Použít" → auto-fill Part fields
5. Save Part → reload stock cost → recalculate batches

---

## Architectural Decisions

### **Why 3 Phases?**

| Phase | Tech | Cost | Value | When |
|-------|------|------|-------|------|
| **1. Regex** | Python stdlib | Low | High | NOW (Materials) |
| **2. Fuzzy** | Meilisearch | Medium | High | Q2 2026 (Multi-module) |
| **3. AI** | ML pipeline | High | Medium | Q4 2026 (If needed) |

**Trade-offs:**
- ✅ Incremental complexity (KISS principle)
- ✅ Avoid over-engineering (AI v1.0 = overkill)
- ✅ Each phase adds real value
- ✅ Reusable infrastructure (Fáze 2/3 serve all modules)
- ❌ Fáze 1 není reusable (specific to Materials)
- ❌ Re-write risk (pokud Fáze 1 nestačí)

### **Why NOT AI in Fáze 1?**

| Criteria | Regex (Fáze 1) | AI (Fáze 3) |
|----------|----------------|-------------|
| **Effort** | 12h | 40h |
| **Dependencies** | None | Transformers, Qdrant, models |
| **Maintenance** | Low | High (model updates) |
| **Accuracy** | 90% (structured input) | 95% (semantic queries) |
| **Latency** | < 50ms | < 200ms |
| **Value NOW** | High (Materials) | Low (1 use case) |

**Conclusion:** Regex stačí pro 90% use cases v1.0-v3.0. AI až když je jasná hodnota (v5.0 Tech DB).

### **Reusability Strategy**

**Fáze 1:** Material-specific (NOT reusable)
- Tightly coupled to Material domain
- Hardcoded regex patterns pro shapes/norms
- No abstraction layer

**Fáze 2:** Generic Search Service (REUSABLE)
```python
# app/services/search_service.py

class SearchService:
    async def search(
        query: str,
        entity_type: str,  # "part", "customer", "drawing", "material"
        filters: dict = None
    ) -> List[SearchResult]:
        """Unified search API pro všechny moduly"""
```

**Fáze 3:** AI Search Layer (REUSABLE)
```python
# app/services/ai_search_service.py

class AISearchService:
    async def semantic_search(
        query: str,
        context: dict = None
    ) -> List[AISearchResult]:
        """Semantic search s embeddings"""
```

---

## Test Coverage

**Unit tests:** 25+ test cases
- Happy paths (D20 C45 100mm, 20x30 S235, t2 1.4301, atd.)
- Edge cases (lowercase, extra whitespace, decimals)
- Partial matches (jen shape, jen material)
- No matches (nesmysl, prázdný string)
- DB lookups (MaterialGroup, PriceCategory, MaterialItem)
- Confidence scoring
- Unicode symbols (Ø, □, ⬡)

**Integration tests:** Manual (QA)
- UI flow: type → parse → apply → save
- Debounce behavior
- Error handling
- Cross-browser (Chrome, Firefox, Safari)

---

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Parse accuracy** | >90% for common formats | Unit tests pass rate |
| **API latency** | <200ms | Logging |
| **User adoption** | >50% use quick input | Analytics (parse API calls) |
| **Confidence distribution** | >70% results with confidence >0.7 | Logging |

---

## Migration Path

### **v1.4 → v2.5 (Fáze 1 → Fáze 2):**
- Keep Material Parser pro backward compatibility
- Add Meilisearch for fuzzy matching
- Material quick input can use BOTH (regex first, fuzzy fallback)

### **v2.5 → v5.0 (Fáze 2 → Fáze 3):**
- Add AI layer on top of Meilisearch
- Use AI only for complex queries (heuristic: >5 words)
- Fallback chain: AI → Fuzzy → Exact

---

## Future Considerations

### **Fáze 2 Triggers:**
- [x] Materials need search ✅ (DONE)
- [ ] Quotes need Part search (v2.0)
- [ ] PLM needs Drawing search (v3.0)
- **Decision point:** When >3 modules need search → implement Meilisearch

### **Fáze 3 Triggers:**
- [ ] Tech DB queries are too complex for fuzzy (v5.0)
- [ ] Users request "find similar parts" feature
- [ ] Semantic recommendations have clear value

---

## Alternatives Considered

### **Alternative 1: Elasticsearch**
- **Pros:** Powerful, battle-tested
- **Cons:** Heavy (JVM), complex setup, overkill for GESTIMA
- **Decision:** Rejected (Meilisearch lighter + easier)

### **Alternative 2: PostgreSQL Full-Text**
- **Pros:** No extra dependency (when we migrate from SQLite)
- **Cons:** No typo tolerance, slower, less features than Meilisearch
- **Decision:** Possible fallback if Meilisearch problematic

### **Alternative 3: OpenAI API (Cloud AI)**
- **Pros:** Zero ML maintenance
- **Cons:** Cloud dependency (GESTIMA = in-house only!), cost, latency
- **Decision:** Rejected (violates VIS-007: Single Database / In-House)

---

## References

- [VISION.md](../VISION.md) - Roadmap, modules, timeline
- [VIS-007](../VISION.md#vis-007-single-database-no-microservices) - In-house only policy
- [ADR-015](015-material-norm-mapping.md) - MaterialNorm design (DB lookup foundation)
- [CLAUDE.md - WZORY](../../CLAUDE.md#wzory) - Regex pattern examples
- [L-013](../../CLAUDE.md#l-013-debounced-race--nan) - Debounce pattern (applied to parser)

---

## Changelog

- **2026-01-27:** Created ADR-016 (Fáze 1 implemented)
- **Future:** Update when Fáze 2/3 are implemented

---

**Next Review:** Q2 2026 (po v2.0 deployment - evaluate Meilisearch need)
**Owner:** Development Team
**Status:** IMPLEMENTED (Fáze 1 ✅)
