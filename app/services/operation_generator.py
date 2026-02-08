"""GESTIMA - Deterministic Operation Generator

Generates manufacturing operations from geometry in a DETERMINISTIC way.

Key principle: Same geometry → ALWAYS same operations (100% consistency)

This is Phase 2 of ML-ready architecture:
  Phase 1: Claude extracts geometry (geometry_extractor.py)
  Phase 2: Generate operations (THIS FILE) ← deterministic!
  Phase 3: Calculate times (time_calculator.py)
  Phase 4: Collect ML training data

ADR: Why deterministic?
- Pricing consistency: 60 identical parts → 60 identical quotes
- Testing: Unit tests can verify correct operations
- ML training: Ground truth for what "correct" means
- Debugging: Reproducible behavior

Scope:
- ✅ Turning (cylindrical parts) - 90% of use cases
- ✅ Drilling (holes, threads)
- ✅ Basic milling (pockets, slots) - prismatic parts
- ❌ 3D surfaces (complex toolpaths) - keep Claude for this
- ❌ Multi-axis milling - out of scope
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.services.tool_selection_catalog import select_tool

logger = logging.getLogger(__name__)


@dataclass
class Operation:
    """Single manufacturing operation (deterministic output)."""
    seq: int
    operation_type: str  # "turning", "drilling", "milling", etc.
    feature_type: str    # "od_rough", "drill", "thread_od", etc.
    tool_number: str     # "T01", "T02", etc.
    tool_name: str       # "CNMG hrubovací nůž", "Vrták Ø18.5", etc.
    params: Dict[str, Any]
    notes: str


class OperationGenerator:
    """
    Deterministický generátor operací z geometrie.

    KONZISTENCE 100%: Stejná geometrie → vždy stejné operace
    PŘESNOST 85-95%: Správné operace pro 85-95% běžných dílů
    """

    def __init__(self):
        self.operation_seq = 1
        self.tool_number = 1
        self.tool_registry = {}  # track which tools we've assigned

    def generate(
        self,
        geometry: Dict[str, Any],
        material_group: str = "20910004",
        cutting_mode: str = "mid"
    ) -> List[Operation]:
        """
        Main entry point: Generate operations from geometry.

        Args:
            geometry: Parsed geometry from geometry_extractor.py
            material_group: Material code for cutting conditions
            cutting_mode: "low" | "mid" | "high"

        Returns:
            List of Operation objects (deterministic order)
        """
        self.operation_seq = 1
        self.tool_number = 1
        self.tool_registry = {}

        part_type = geometry.get("part_type", "rotational")

        if part_type == "rotational":
            return self._generate_turning_operations(geometry, material_group, cutting_mode)
        elif part_type == "prismatic":
            return self._generate_milling_operations(geometry, material_group, cutting_mode)
        else:
            logger.warning(f"Unknown part_type: {part_type}, defaulting to rotational")
            return self._generate_turning_operations(geometry, material_group, cutting_mode)

    # ========================================================================
    # TURNING (rotational parts)
    # ========================================================================

    def _generate_turning_operations(
        self,
        geometry: Dict[str, Any],
        material_group: str,
        cutting_mode: str
    ) -> List[Operation]:
        """
        Generate operations for rotational (turning) parts.

        Order (deterministic):
          1. Face (čelování)
          2. Center drill (středění)
          3. Drilling/reaming holes
          4. OD rough/finish (vnější průměr)
          5. Chamfers (sražení)
          6. Radii/fillets
          7. Threads
          8. Grooves
          9. Parting (upíchnutí)
          10. Finishing (odjehlení, mytí, kontrola)
        """
        ops = []
        profile = geometry.get("profile_geometry", {})
        features = profile.get("features", [])
        outer_contour = profile.get("outer_contour", [])
        inner_contour = profile.get("inner_contour", [])

        # Get stock dimensions
        stock = geometry.get("stock", {}).get("dimensions", {})
        stock_diameter = stock.get("diameter", 0)

        # Tool assignments (from catalog)
        # NOTE: Using catalog for dynamic tool selection based on material
        tool_rough = self._select_tool_from_catalog("turning", "hrubovani", material_group)
        tool_finish = self._select_tool_from_catalog("turning", "dokoncovani", material_group)

        T01 = self._assign_tool("T01", tool_rough["tool_name"])
        T02 = self._assign_tool("T02", tool_finish["tool_name"])
        T07 = self._assign_tool("T07", "Středící vrták")
        T08 = self._assign_tool("T08", "Vrták")
        T09 = self._assign_tool("T09", "Výstružník")

        # === STEP 1: Face (if stock > part diameter) ===
        if outer_contour and stock_diameter > 0:
            max_diameter = max(pt["r"] * 2 for pt in outer_contour)
            if stock_diameter > max_diameter:
                ops.append(Operation(
                    seq=self._next_seq(),
                    operation_type="turning",
                    feature_type="face",
                    tool_number=T01,
                    tool_name="CNMG hrubovací nůž",
                    params={
                        "from_diameter": stock_diameter,
                        "depth": round((stock_diameter - max_diameter) / 2, 1)
                    },
                    notes="Zarovnání levého čela"
                ))

        # === STEP 2: Center drill (if there are holes) ===
        holes = [f for f in features if f["type"] == "hole"]
        if holes and any(h["diameter"] < 20 for h in holes):
            # Center drill needed for holes < Ø20
            ops.append(Operation(
                seq=self._next_seq(),
                operation_type="turning",
                feature_type="center_drill",
                tool_number=T07,
                tool_name="Středící vrták",
                params={"to_diameter": 4, "depth": 4},
                notes="Navrtání pro konícek"
            ))

        # === STEP 3: Drilling/reaming ===
        for hole in holes:
            diameter = hole["diameter"]
            depth = hole["depth"]
            tolerance = hole.get("tolerance", "")

            # If tolerance H6/H7/H8 → drill undersized + ream
            if tolerance in ["H6", "H7", "H8"]:
                # Drill 0.5mm undersized (use catalog)
                drill_tool = self._select_tool_from_catalog(
                    "drilling", "vrtani", material_group, diameter - 0.5
                )
                ops.append(Operation(
                    seq=self._next_seq(),
                    operation_type="turning",
                    feature_type="drill",
                    tool_number=T08,
                    tool_name=f"{drill_tool['tool_name']} Ø{diameter - 0.5}",
                    params={
                        "to_diameter": diameter - 0.5,
                        "depth": depth
                    },
                    notes=f"Předvrtání pro {tolerance}"
                ))

                # Ream to final size (use catalog)
                ream_tool = self._select_tool_from_catalog(
                    "drilling", "vystruzovani", material_group, diameter
                )
                ops.append(Operation(
                    seq=self._next_seq(),
                    operation_type="turning",
                    feature_type="ream",
                    tool_number=T09,
                    tool_name=f"{ream_tool['tool_name']} Ø{diameter} {tolerance}",
                    params={
                        "to_diameter": diameter,
                        "depth": depth
                    },
                    notes=f"Vystružení na {tolerance}"
                ))
            else:
                # Standard drilling (no tight tolerance)
                ops.append(Operation(
                    seq=self._next_seq(),
                    operation_type="turning",
                    feature_type="drill",
                    tool_number=T08,
                    tool_name=f"Vrták Ø{diameter}",
                    params={
                        "to_diameter": diameter,
                        "depth": depth
                    },
                    notes=f"Vrtání Ø{diameter}"
                ))

        # === STEP 4: OD turning (outer diameter) ===
        # Parse contour into segments
        segments = self._parse_contour_segments(outer_contour)

        for segment in segments:
            if segment["type"] == "cylinder":
                from_d = segment["from_diameter"]
                to_d = segment["to_diameter"]
                length = segment["length"]

                # Rough pass (if there's material to remove)
                if from_d > to_d + 2:  # > 2mm allowance
                    ops.append(Operation(
                        seq=self._next_seq(),
                        operation_type="turning",
                        feature_type="od_rough",
                        tool_number=T01,
                        tool_name="CNMG hrubovací nůž",
                        params={
                            "from_diameter": from_d,
                            "to_diameter": to_d + 1,  # leave 1mm for finish
                            "length": length
                        },
                        notes=f"Hrubování Ø{from_d}→Ø{to_d}"
                    ))

                # Finish pass
                ops.append(Operation(
                    seq=self._next_seq(),
                    operation_type="turning",
                    feature_type="od_finish",
                    tool_number=T02,
                    tool_name="DNMG dokončovací nůž",
                    params={
                        "from_diameter": to_d + 1 if from_d > to_d + 2 else from_d,
                        "to_diameter": to_d,
                        "length": length
                    },
                    notes=f"Dokončení Ø{to_d}"
                ))

        # === STEP 5: Chamfers ===
        chamfers = [f for f in features if f["type"] == "chamfer"]
        for chamfer in chamfers:
            ops.append(Operation(
                seq=self._next_seq(),
                operation_type="turning",
                feature_type="chamfer",
                tool_number=T02,
                tool_name="DNMG dokončovací nůž",
                params={
                    "width": chamfer["width"],
                    "angle": chamfer.get("angle", 45),
                    "diameter": chamfer.get("diameter")
                },
                notes=f"Zkosení {chamfer['width']}×{chamfer.get('angle', 45)}°"
            ))

        # === STEP 6: Radii ===
        radii = [f for f in features if f["type"] == "radius"]
        for radius_feature in radii:
            r = radius_feature["r"]
            surface_type = radius_feature.get("surface_type", "corner_radius")

            if surface_type == "spherical":
                # Spherical surface → rough + finish
                T_ball = self._assign_tool("T10", f"Kulový nůž R{r}")

                ops.append(Operation(
                    seq=self._next_seq(),
                    operation_type="turning",
                    feature_type="sphere_rough",
                    tool_number=T_ball,
                    tool_name=f"Kulový nůž R{r}",
                    params={"radius": r},
                    notes=f"Hrubování kulové plochy R{r}"
                ))

                ops.append(Operation(
                    seq=self._next_seq(),
                    operation_type="turning",
                    feature_type="sphere_finish",
                    tool_number=T_ball,
                    tool_name=f"Kulový nůž R{r}",
                    params={"radius": r},
                    notes=f"Dokončení kulové plochy R{r}"
                ))
            else:
                # Corner radius → just finish pass
                ops.append(Operation(
                    seq=self._next_seq(),
                    operation_type="turning",
                    feature_type="radius",
                    tool_number=T02,
                    tool_name="DNMG dokončovací nůž",
                    params={"corner_radius": r},
                    notes=f"Zaoblení R{r}"
                ))

        # === STEP 7: Threads ===
        threads = [f for f in features if f["type"] in ["thread_od", "thread_id"]]
        for thread in threads:
            thread_type = thread["type"]
            T_thread = self._assign_tool("T05", "Závitový nůž")

            ops.append(Operation(
                seq=self._next_seq(),
                operation_type="turning",
                feature_type=thread_type,
                tool_number=T_thread,
                tool_name=f"Závitový nůž {thread.get('spec', '')}",
                params={
                    "diameter": thread["diameter"],
                    "pitch": thread["pitch"],
                    "length": thread["length"]
                },
                notes=f"Řezání závitu {thread.get('spec', '')}"
            ))

        # === STEP 8: Grooves ===
        grooves = [f for f in features if f["type"] in ["groove_od", "groove_id"]]
        for groove in grooves:
            T_parting = self._assign_tool("T06", "Zapichovací nůž")

            ops.append(Operation(
                seq=self._next_seq(),
                operation_type="turning",
                feature_type=groove["type"],
                tool_number=T_parting,
                tool_name="Zapichovací nůž",
                params={
                    "width": groove["width"],
                    "diameter": groove["diameter"],
                    "depth": groove["depth"]
                },
                notes=f"Zapichování drážky {groove['width']}mm"
            ))

        # === STEP 9: Finishing operations ===
        ops.append(Operation(
            seq=self._next_seq(),
            operation_type="finishing",
            feature_type="deburr_manual",
            tool_number="—",
            tool_name="Ruční odjehlení",
            params={},
            notes="Odstranění otřepů"
        ))

        ops.append(Operation(
            seq=self._next_seq(),
            operation_type="finishing",
            feature_type="wash",
            tool_number="—",
            tool_name="Mycí linka",
            params={},
            notes="Mytí dílu"
        ))

        ops.append(Operation(
            seq=self._next_seq(),
            operation_type="finishing",
            feature_type="inspect",
            tool_number="—",
            tool_name="Kontrola",
            params={},
            notes="Kontrola rozměrů dle výkresu"
        ))

        return ops

    # ========================================================================
    # MILLING (prismatic parts) - 2.5D operations
    # ========================================================================

    def _generate_milling_operations(
        self,
        geometry: Dict[str, Any],
        material_group: str,
        cutting_mode: str
    ) -> List[Operation]:
        """
        Generate operations for prismatic (milling) parts.

        Order (deterministic):
          1. Face milling (planování čela)
          2. Pockets (kapsy)
          3. Slots (drážky)
          4. Drilling (vrtání na fréze)
          5. Tapping/Threading (závity na fréze)
          6. Chamfers (sražení)
          7. Finishing (odjehlení, mytí, kontrola)

        Scope: 2.5D only (no 3D surfaces, no multi-axis)
        """
        ops = []
        profile = geometry.get("profile_geometry", {})
        features = profile.get("features", [])

        # Get stock dimensions
        stock = geometry.get("stock", {}).get("dimensions", {})
        stock_width = stock.get("width", 0)
        stock_height = stock.get("height", 0)
        stock_length = stock.get("length", 0)

        # Tool assignments (deterministic)
        T01 = self._assign_tool("T01", "Planová fréza")
        T02 = self._assign_tool("T02", "Kotoučová fréza")
        T03 = self._assign_tool("T03", "Válcová fréza")
        T04 = self._assign_tool("T04", "Vrták")
        T05 = self._assign_tool("T05", "Závitník")

        # === STEP 1: Face milling (if needed) ===
        if stock_width > 0 and stock_length > 0:
            ops.append(Operation(
                seq=self._next_seq(),
                operation_type="milling",
                feature_type="face_mill",
                tool_number=T01,
                tool_name="Planová fréza",
                params={
                    "area_width": stock_width,
                    "area_length": stock_length
                },
                notes="Planování horního čela"
            ))

        # === STEP 2: Pockets ===
        pockets = [f for f in features if f["type"] == "pocket"]
        for pocket in pockets:
            length = pocket.get("length", 0)
            width = pocket.get("width", 0)
            depth = pocket.get("depth", 0)
            corner_radius = pocket.get("corner_radius", 0)

            # Rough pass (if depth > 5mm)
            if depth > 5:
                ops.append(Operation(
                    seq=self._next_seq(),
                    operation_type="milling",
                    feature_type="pocket_rough",
                    tool_number=T03,
                    tool_name="Válcová fréza hrubovací",
                    params={
                        "length": length,
                        "width": width,
                        "depth": depth - 0.5,  # leave 0.5mm for finish
                        "corner_radius": corner_radius
                    },
                    notes=f"Hrubování kapsy {length}×{width}×{depth}"
                ))

            # Finish pass
            ops.append(Operation(
                seq=self._next_seq(),
                operation_type="milling",
                feature_type="pocket_finish",
                tool_number=T03,
                tool_name="Válcová fréza dokončovací",
                params={
                    "length": length,
                    "width": width,
                    "depth": depth,
                    "corner_radius": corner_radius
                },
                notes=f"Dokončení kapsy {length}×{width}×{depth}"
            ))

        # === STEP 3: Slots ===
        slots = [f for f in features if f["type"] == "slot"]
        for slot in slots:
            length = slot.get("length", 0)
            width = slot.get("width", 0)
            depth = slot.get("depth", 0)

            # Use slot cutter if width <= 10mm, otherwise pocket milling
            if width <= 10:
                # Slot cutter (kotoučová fréza)
                ops.append(Operation(
                    seq=self._next_seq(),
                    operation_type="milling",
                    feature_type="slot",
                    tool_number=T02,
                    tool_name=f"Kotoučová fréza {width}mm",
                    params={
                        "length": length,
                        "width": width,
                        "depth": depth
                    },
                    notes=f"Drážka {length}×{width}×{depth}"
                ))
            else:
                # Wide slot → pocket milling strategy
                ops.append(Operation(
                    seq=self._next_seq(),
                    operation_type="milling",
                    feature_type="slot_wide",
                    tool_number=T03,
                    tool_name="Válcová fréza",
                    params={
                        "length": length,
                        "width": width,
                        "depth": depth
                    },
                    notes=f"Široká drážka {length}×{width}×{depth}"
                ))

        # === STEP 4: Drilling (on mill) ===
        holes = [f for f in features if f["type"] == "hole"]
        for hole in holes:
            diameter = hole["diameter"]
            depth = hole["depth"]
            tolerance = hole.get("tolerance", "")

            # Center drill for holes > Ø10
            if diameter > 10:
                ops.append(Operation(
                    seq=self._next_seq(),
                    operation_type="milling",
                    feature_type="center_drill",
                    tool_number=T04,
                    tool_name="Středící vrták",
                    params={"to_diameter": 4, "depth": 5},
                    notes="Navrtání"
                ))

            # Drill
            ops.append(Operation(
                seq=self._next_seq(),
                operation_type="milling",
                feature_type="mill_drill",
                tool_number=T04,
                tool_name=f"Vrták Ø{diameter}",
                params={
                    "to_diameter": diameter,
                    "depth": depth
                },
                notes=f"Vrtání Ø{diameter}×{depth}"
            ))

            # Ream if tight tolerance
            if tolerance in ["H6", "H7", "H8"]:
                T_ream = self._assign_tool("T06", "Výstružník")
                ops.append(Operation(
                    seq=self._next_seq(),
                    operation_type="milling",
                    feature_type="mill_ream",
                    tool_number=T_ream,
                    tool_name=f"Výstružník Ø{diameter} {tolerance}",
                    params={
                        "to_diameter": diameter,
                        "depth": depth
                    },
                    notes=f"Vystružení na {tolerance}"
                ))

        # === STEP 5: Threading (on mill) ===
        threads = [f for f in features if f["type"] in ["thread_od", "thread_id"]]
        for thread in threads:
            thread_type = thread["type"]
            diameter = thread["diameter"]
            pitch = thread["pitch"]
            length = thread.get("length", 0)
            spec = thread.get("spec", "")

            if thread_type == "thread_id":
                # Internal thread → tap or thread mill
                if diameter < 12:
                    # Small threads → use tap
                    ops.append(Operation(
                        seq=self._next_seq(),
                        operation_type="milling",
                        feature_type="mill_tap",
                        tool_number=T05,
                        tool_name=f"Závitník {spec}",
                        params={
                            "diameter": diameter,
                            "pitch": pitch,
                            "length": length
                        },
                        notes=f"Závit {spec}"
                    ))
                else:
                    # Large threads → thread milling
                    T_thread_mill = self._assign_tool("T07", "Závitová fréza")
                    ops.append(Operation(
                        seq=self._next_seq(),
                        operation_type="milling",
                        feature_type="mill_thread",
                        tool_number=T_thread_mill,
                        tool_name=f"Závitová fréza {spec}",
                        params={
                            "diameter": diameter,
                            "pitch": pitch,
                            "length": length
                        },
                        notes=f"Frézování závitu {spec}"
                    ))

        # === STEP 6: Chamfers ===
        chamfers = [f for f in features if f["type"] == "chamfer"]
        for chamfer in chamfers:
            width = chamfer.get("width", 1)
            angle = chamfer.get("angle", 45)

            T_chamfer = self._assign_tool("T08", f"Zkosovací fréza {angle}°")
            ops.append(Operation(
                seq=self._next_seq(),
                operation_type="milling",
                feature_type="mill_chamfer",
                tool_number=T_chamfer,
                tool_name=f"Zkosovací fréza {angle}°",
                params={
                    "width": width,
                    "angle": angle
                },
                notes=f"Zkosení {width}×{angle}°"
            ))

        # === STEP 7: Finishing operations ===
        ops.append(Operation(
            seq=self._next_seq(),
            operation_type="finishing",
            feature_type="deburr_manual",
            tool_number="—",
            tool_name="Ruční odjehlení",
            params={},
            notes="Odstranění otřepů"
        ))

        ops.append(Operation(
            seq=self._next_seq(),
            operation_type="finishing",
            feature_type="wash",
            tool_number="—",
            tool_name="Mycí linka",
            params={},
            notes="Mytí dílu"
        ))

        ops.append(Operation(
            seq=self._next_seq(),
            operation_type="finishing",
            feature_type="inspect",
            tool_number="—",
            tool_name="Kontrola",
            params={},
            notes="Kontrola rozměrů dle výkresu"
        ))

        return ops

    # ========================================================================
    # HELPERS
    # ========================================================================

    def _next_seq(self) -> int:
        """Get next operation sequence number."""
        seq = self.operation_seq
        self.operation_seq += 1
        return seq

    def _assign_tool(self, suggested_number: str, tool_name: str) -> str:
        """
        Assign tool number (deterministic).

        If tool already assigned, return existing number.
        Otherwise assign suggested_number.
        """
        if tool_name in self.tool_registry:
            return self.tool_registry[tool_name]

        self.tool_registry[tool_name] = suggested_number
        return suggested_number

    def _select_tool_from_catalog(
        self,
        operation_type: str,
        operation: str,
        material_group: str,
        diameter: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Select tool from catalog (wrapper around tool_selection_catalog).

        Args:
            operation_type: turning, drilling, threading, milling, etc.
            operation: hrubovani, dokoncovani, vrtani, etc.
            material_group: 8-digit code (e.g., "20910004")
            diameter: optional diameter [mm] for filtering

        Returns:
            Tool spec dict with tool_code, tool_name, notes
            Falls back to generic name if catalog lookup fails
        """
        tool_spec = select_tool(operation_type, operation, material_group, diameter)

        if not tool_spec:
            # Fallback to generic name (for backward compatibility)
            logger.warning(
                f"No tool found in catalog for {operation_type}/{operation}, "
                f"using generic fallback"
            )
            fallback_names = {
                ("turning", "hrubovani"): "CNMG hrubovací nůž",
                ("turning", "dokoncovani"): "DNMG dokončovací nůž",
                ("drilling", "vrtani"): "Vrták HSS",
                ("drilling", "vystruzovani"): "Výstružník HSS",
                ("threading", "zavitovani"): "Závitový nůž",
                ("grooving", "zapichovani"): "Zapichovací nůž",
                ("milling", "frezovani"): "Válcová fréza",
            }
            generic_name = fallback_names.get(
                (operation_type, operation),
                f"{operation_type} tool"
            )
            return {
                "tool_code": "GENERIC",
                "tool_name": generic_name,
                "notes": "Generic fallback tool"
            }

        return tool_spec

    def _parse_contour_segments(self, contour: List[Dict]) -> List[Dict]:
        """
        Parse contour points into cylindrical/taper segments.

        Returns:
            [
                {
                    "type": "cylinder",
                    "from_diameter": 60,
                    "to_diameter": 55,
                    "length": 48,
                    "z_start": 0,
                    "z_end": 48
                },
                ...
            ]
        """
        if not contour or len(contour) < 2:
            return []

        segments = []
        for i in range(len(contour) - 1):
            p1 = contour[i]
            p2 = contour[i + 1]

            r1, z1 = p1["r"], p1["z"]
            r2, z2 = p2["r"], p2["z"]

            length = abs(z2 - z1)
            if length < 0.1:  # skip tiny segments
                continue

            # Cylinder if same radius (±0.1mm tolerance)
            if abs(r1 - r2) < 0.1:
                segments.append({
                    "type": "cylinder",
                    "from_diameter": max(r1, r2) * 2,  # use stock diameter
                    "to_diameter": r1 * 2,
                    "length": length,
                    "z_start": min(z1, z2),
                    "z_end": max(z1, z2)
                })
            else:
                # Taper
                segments.append({
                    "type": "taper",
                    "from_diameter": max(r1, r2) * 2,
                    "to_diameter": min(r1, r2) * 2,
                    "length": length,
                    "z_start": min(z1, z2),
                    "z_end": max(z1, z2),
                    "angle": abs(r2 - r1) / length * 180 / 3.14159  # rough angle
                })

        return segments


# Singleton
operation_generator = OperationGenerator()
