# ADR-027: Part Copy - Operation Sequence Renumbering

**Status:** ✅ Accepted
**Date:** 2026-02-01
**Context:** Part copy feature implementation
**Version:** 1.12.1

---

## Context

When copying a part with operations, we need to decide whether to preserve the original `seq` (sequence) values or renumber them to a clean sequence.

### Problem

Operations use `seq` field for ordering with gaps (10, 20, 30...) to allow drag & drop insertions. After manual reordering, original operations might have irregular sequences (e.g., 5, 15, 25, 42, 55).

**Options:**
1. **Preserve seq** - Copy exact sequence numbers from source
2. **Renumber seq** - Reset to clean 10, 20, 30... sequence

---

## Decision

**We will RENUMBER operations to clean 10, 20, 30... sequence when copying.**

### Rationale

#### User Experience
- **Clean Start** - Every copied part begins with organized sequence
- **Consistency** - Copied parts match newly created parts (both start at 10, 20, 30...)
- **Predictability** - Users know copied parts have standard spacing

#### Technical Benefits
- **Drag & Drop Ready** - Ample gaps for future insertions
- **No Confusion** - Clear that it's a new part, not a clone with history
- **Maintainability** - Standard sequence = easier debugging

#### Edge Case Handling
```python
# Source part (after drag & drop reordering)
Operations: seq 5, 15, 25, 42, 55

# Copied part (renumbered)
Operations: seq 10, 20, 30, 40, 50
```

---

## Implementation

### Backend: `copy_part_relations`

```python
# Copy operations if requested
if copy_operations:
    result = await db.execute(
        select(Operation).where(Operation.part_id == source_part.id).order_by(Operation.seq)
    )
    source_operations = result.scalars().all()

    # Renumber operations to clean 10, 20, 30... sequence
    new_seq = 10
    for src_op in source_operations:
        new_op = Operation(
            part_id=target_part.id,
            seq=new_seq,  # Clean sequence: 10, 20, 30...
            # ... other fields ...
        )
        db.add(new_op)
        new_seq += 10  # Increment by 10 for next operation
```

### Key Points
1. **Order by seq** - Ensures correct order from source
2. **Start at 10** - Consistent with new parts
3. **Increment by 10** - Standard gap for drag & drop
4. **Preserve order** - Maintains logical operation sequence

---

## Alternatives Considered

### Alternative 1: Preserve Original Seq
**Rejected** because:
- ❌ Irregular numbers (5, 15, 25, 42) confusing for users
- ❌ Inconsistent with newly created parts
- ❌ No benefit - seq is just ordering, not semantic

### Alternative 2: Custom Seq Offset
**Rejected** because:
- ❌ Overly complex (start at 100? 1000?)
- ❌ No clear advantage over clean 10, 20, 30...
- ❌ Harder to understand system behavior

---

## Consequences

### Positive
- ✅ **Clean UX** - Every copied part has organized operations
- ✅ **Consistency** - All parts (new or copied) follow same pattern
- ✅ **Maintainability** - Predictable sequence numbering

### Neutral
- ⚪ **Lost Info** - Original seq values discarded (not needed)
- ⚪ **Extra Code** - Renumbering adds ~3 lines of code

### Negative
- ❌ **None identified** - No drawbacks to this approach

---

## Related

- **ADR-026:** Universal Module Pattern - Copy functionality follows module pattern
- **PartDetailPanel.vue** - UI integration with copy button
- **CopyPartModal.vue** - Modal workflow for part copying
- **parts_router.py:copy_part_relations** - Backend implementation

---

## Notes

### Drag & Drop Context
Operations use `seq` for ordering, not identification:
- **Drag op 20 before op 10** → op 20 gets seq=5 (DB write)
- **Not a rename** → Operation still has same ID/name
- **Just reordering** → Only seq changes

### Copy Behavior
```
Original part (after drag & drop):
- Operation A: seq=15  ← dragged from 10
- Operation B: seq=25
- Operation C: seq=30

Copied part (renumbered):
- Operation A: seq=10  ← clean start
- Operation B: seq=20
- Operation C: seq=30
```

---

**Decision By:** Claude + User
**Implemented:** 2026-02-01
**Status:** ✅ Production Ready
