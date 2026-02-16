"""GESTIMA - Purchase Price Analyzer

Analyzes purchase order data from Infor SLPoItems IDO,
maps to PriceCategories, and computes real weighted averages
per weight tier — no hardcoded coefficients.

Data flow:
  Infor SLPoItems → fetch (paginated) → parse Item codes → resolve PriceCategory
  → segment by QtyReceived into tier ranges → compute weighted avg per tier
  → compare with current PriceTier values → return analysis
"""

import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.material import (
    MaterialGroup,
    MaterialPriceCategory,
    MaterialPriceTier,
    StockShape,
)
from app.models.material_norm import MaterialNorm
from app.schemas.purchase_prices import (
    PriceCategoryAnalysis,
    PurchasePriceAnalysisResponse,
    SuggestedBoundary,
    TierAnalysis,
    UnmatchedItem,
    WeightDistribution,
)
from app.services.infor_api_client import InforAPIClient
from app.services.infor_material_importer import MaterialImporter

logger = logging.getLogger(__name__)

# Max pages to fetch (safety limit against infinite pagination)
MAX_PAGES = 50
PAGE_SIZE = 500

SLPOITEMS_PROPERTIES = [
    "PoNum", "PoLine", "Item", "Description",
    "QtyOrdered", "QtyReceived", "ItemCost",
    "DerTotalRcvdCost", "UM", "PoOrderDate",
    "DueDate", "RcvdDate", "PoVendNum",
    "VenadrName", "Stat",
]


class PurchasePriceAnalyzer:
    """Analyzes purchase prices from Infor SLPoItems and maps to PriceCategories."""

    def __init__(self, infor_client: InforAPIClient, db: AsyncSession):
        self.client = infor_client
        self.db = db
        self._importer = MaterialImporter()

        # Pre-loaded lookup caches (populated in _preload_lookups)
        self._norm_by_wnr: Dict[str, int] = {}          # w_nr -> material_group_id
        self._norm_by_prefix: Dict[str, int] = {}        # w_nr prefix (1.0) -> material_group_id
        self._category_by_group_shape: Dict[Tuple[int, str], int] = {}  # (group_id, shape) -> cat_id
        self._categories: Dict[int, MaterialPriceCategory] = {}  # cat_id -> category
        self._groups: Dict[int, MaterialGroup] = {}              # group_id -> group
        self._tiers_by_category: Dict[int, List[MaterialPriceTier]] = {}  # cat_id -> [tier, ...]

    async def analyze(self, year_from: int = 2024, year_to: Optional[int] = None) -> PurchasePriceAnalysisResponse:
        """Main analysis: fetch PO items, map to categories, aggregate per tier.

        Args:
            year_from: Start year (inclusive)
            year_to: End year (inclusive). If None, same as year_from (single year).
        """
        if year_to is None:
            year_to = year_from

        start = time.time()

        # Pre-load all lookup data into memory (avoid N+1 queries)
        await self._preload_lookups()

        # Fetch all PO items from Infor
        raw_items = await self._fetch_all_po_items(year_from, year_to)
        fetch_time = time.time() - start

        date_label = f"{year_from}" if year_from == year_to else f"{year_from}-{year_to}"

        if not raw_items:
            return PurchasePriceAnalysisResponse(
                year_from=year_from,
                date_range=f"{date_label} (0 rows)",
                total_po_lines_fetched=0,
                total_po_lines_matched=0,
                total_po_lines_unmatched=0,
                unique_materials=0,
                categories=[],
                unmatched=[],
                cached=False,
                fetch_time_seconds=round(fetch_time, 1),
            )

        # Parse and resolve each PO item
        matched, unmatched_raw, w_nr_set = self._resolve_items(raw_items)

        # Aggregate per PriceCategory + per tier
        categories = self._aggregate(matched)

        # Collect unmatched summary
        unmatched = self._summarize_unmatched(unmatched_raw)

        # Date range from data
        dates = [r.get("PoOrderDate", "") for r in raw_items if r.get("PoOrderDate")]
        date_min = min(dates)[:10].replace(" ", "") if dates else f"{year_from}-01-01"
        date_max = max(dates)[:10].replace(" ", "") if dates else "now"

        return PurchasePriceAnalysisResponse(
            year_from=year_from,
            date_range=f"{date_min} to {date_max}",
            total_po_lines_fetched=len(raw_items),
            total_po_lines_matched=len(matched),
            total_po_lines_unmatched=len(unmatched_raw),
            unique_materials=len(w_nr_set),
            categories=categories,
            unmatched=unmatched,
            cached=False,
            fetch_time_seconds=round(time.time() - start, 1),
        )

    # ── Infor fetch ──────────────────────────────────────────────

    async def _fetch_all_po_items(self, year_from: int, year_to: int) -> List[Dict[str, Any]]:
        """Paginated fetch of SLPoItems from Infor with deduplication.

        Uses (PoNum, PoLine, Item) as unique key to prevent counting
        the same PO line multiple times across pages.
        """
        filter_expr = (
            f"Item LIKE '1.%' AND DerTotalRcvdCost > 0 "
            f"AND PoOrderDate >= '{year_from}-01-01' "
            f"AND PoOrderDate < '{year_to + 1}-01-01'"
        )

        all_items: List[Dict[str, Any]] = []
        seen_keys: set = set()  # (PoNum, PoLine, Item) dedup
        seen_bookmarks: set = set()
        dup_count = 0
        bookmark = None
        page = 0

        while page < MAX_PAGES:
            page += 1
            result = await self.client.load_collection(
                ido_name="SLPoItems",
                properties=SLPOITEMS_PROPERTIES,
                filter=filter_expr,
                order_by="PoOrderDate DESC",
                record_cap=PAGE_SIZE,
                load_type="NEXT" if bookmark else None,
                bookmark=bookmark,
            )

            data = result.get("data", [])
            new_bookmark = result.get("bookmark")
            has_more = result.get("has_more", False)

            # Detect bookmark loop (same bookmark returned = infinite loop)
            if new_bookmark and new_bookmark in seen_bookmarks:
                logger.warning(
                    f"Bookmark loop detected on page {page} "
                    f"(total {len(all_items)} rows, {dup_count} dups). Stopping."
                )
                break
            if new_bookmark:
                seen_bookmarks.add(new_bookmark)

            # Deduplicate within fetch
            for row in data:
                key = (
                    str(row.get("PoNum", "")),
                    str(row.get("PoLine", "")),
                    str(row.get("Item", "")),
                )
                if key in seen_keys:
                    dup_count += 1
                    continue
                seen_keys.add(key)
                all_items.append(row)

            logger.info(
                f"SLPoItems page {page}: {len(data)} raw, "
                f"{len(all_items)} unique (dups: {dup_count})"
            )

            bookmark = new_bookmark
            if not has_more or not bookmark or not data:
                break

        logger.info(
            f"SLPoItems fetch complete: {len(all_items)} unique rows, "
            f"{dup_count} duplicates removed, {page} pages"
        )
        return all_items

    # ── Pre-load lookups ─────────────────────────────────────────

    async def _preload_lookups(self) -> None:
        """Pre-load MaterialNorms, Groups, Categories, Tiers into dicts."""
        # MaterialNorms → w_nr -> group_id
        result = await self.db.execute(select(MaterialNorm))
        for norm in result.scalars().all():
            if norm.w_nr:
                self._norm_by_wnr[norm.w_nr] = norm.material_group_id
                prefix = norm.w_nr[:3]  # "1.0", "1.4", etc.
                if prefix not in self._norm_by_prefix:
                    self._norm_by_prefix[prefix] = norm.material_group_id

        # MaterialGroups
        result = await self.db.execute(select(MaterialGroup))
        for group in result.scalars().all():
            self._groups[group.id] = group

        # PriceCategories
        result = await self.db.execute(select(MaterialPriceCategory))
        for cat in result.scalars().all():
            self._categories[cat.id] = cat
            if cat.material_group_id and cat.shape:
                self._category_by_group_shape[(cat.material_group_id, cat.shape)] = cat.id

        # PriceTiers (per category, sorted by min_weight)
        result = await self.db.execute(
            select(MaterialPriceTier).order_by(
                MaterialPriceTier.price_category_id,
                MaterialPriceTier.min_weight,
            )
        )
        for tier in result.scalars().all():
            self._tiers_by_category.setdefault(tier.price_category_id, []).append(tier)

        logger.info(
            f"Pre-loaded: {len(self._norm_by_wnr)} norms, "
            f"{len(self._groups)} groups, {len(self._categories)} categories, "
            f"{sum(len(t) for t in self._tiers_by_category.values())} tiers"
        )

    # ── Parse + Resolve ──────────────────────────────────────────

    def _resolve_items(
        self, raw_items: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], set]:
        """Parse Item codes and resolve to PriceCategory. Returns (matched, unmatched, w_nr_set)."""
        matched: List[Dict[str, Any]] = []
        unmatched: List[Dict[str, Any]] = []
        w_nr_set: set = set()

        for row in raw_items:
            item_code = str(row.get("Item", ""))
            qty_received = self._to_float(row.get("QtyReceived", 0))
            total_cost = self._to_float(row.get("DerTotalRcvdCost", 0))

            # Skip zero-qty rows
            if qty_received <= 0 or total_cost <= 0:
                continue

            # Extract W.Nr
            w_nr = self._importer.extract_w_nr_from_item_code(item_code)
            if not w_nr:
                unmatched.append({**row, "_reason": "W.Nr not extracted from Item code"})
                continue

            w_nr_set.add(w_nr)

            # Resolve MaterialGroup (in-memory lookup)
            group_id = self._norm_by_wnr.get(w_nr)
            if not group_id:
                prefix = w_nr[:3]
                group_id = self._norm_by_prefix.get(prefix)
            if not group_id:
                unmatched.append({**row, "_reason": f"No MaterialNorm for W.Nr '{w_nr}'"})
                continue

            # Parse shape from Item code
            dims = self._importer.parse_dimensions_from_item_code(item_code)
            shape = self._importer.parse_shape_from_item_code(item_code, dims)
            if not shape:
                # Fallback: try from Description
                desc = str(row.get("Description", ""))
                shape = self._importer.parse_shape_from_text(desc)
            if not shape:
                unmatched.append({**row, "_reason": f"Shape not detected from '{item_code}'"})
                continue

            shape_value = shape.value if isinstance(shape, StockShape) else shape

            # Resolve PriceCategory (in-memory lookup)
            cat_id = self._category_by_group_shape.get((group_id, shape_value))
            if not cat_id:
                unmatched.append({
                    **row,
                    "_reason": f"No PriceCategory for group={group_id} + shape={shape_value}",
                })
                continue

            # Compute unit price from real data
            unit_price = total_cost / qty_received

            matched.append({
                "cat_id": cat_id,
                "group_id": group_id,
                "w_nr": w_nr,
                "shape": shape_value,
                "qty_received": qty_received,
                "total_cost": total_cost,
                "unit_price": unit_price,
                "order_date": str(row.get("PoOrderDate", "")),
                "vendor_name": str(row.get("VenadrName", "")),
                "vendor_num": str(row.get("PoVendNum", "")),
            })

        logger.info(f"Resolved: {len(matched)} matched, {len(unmatched)} unmatched")
        return matched, unmatched, w_nr_set

    # ── Aggregation ──────────────────────────────────────────────

    def _aggregate(self, matched: List[Dict[str, Any]]) -> List[PriceCategoryAnalysis]:
        """Aggregate matched PO items per PriceCategory with per-tier breakdown."""
        # Group by cat_id
        by_cat: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for item in matched:
            by_cat[item["cat_id"]].append(item)

        results: List[PriceCategoryAnalysis] = []

        for cat_id, items in sorted(by_cat.items()):
            cat = self._categories.get(cat_id)
            if not cat:
                continue

            group = self._groups.get(cat.material_group_id) if cat.material_group_id else None
            tiers_db = self._tiers_by_category.get(cat_id, [])

            # Overall stats
            total_qty = sum(i["qty_received"] for i in items)
            total_cost = sum(i["total_cost"] for i in items)
            weighted_avg = total_cost / total_qty if total_qty > 0 else 0.0
            unit_prices = [i["unit_price"] for i in items]

            # Vendors
            vendor_counts: Dict[str, int] = defaultdict(int)
            for i in items:
                vn = i["vendor_name"]
                if vn:
                    vendor_counts[vn] += 1
            top_vendors = [
                v for v, _ in sorted(vendor_counts.items(), key=lambda x: -x[1])[:3]
            ]

            # Per-tier analysis (segment PO items by QtyReceived into existing tier ranges)
            tier_analyses = self._analyze_tiers(items, tiers_db)

            # Weight distribution + suggested boundaries
            qtys = sorted(i["qty_received"] for i in items)
            weight_dist = self._compute_distribution(qtys, tiers_db) if len(qtys) >= 3 else None

            # Quarterly prices
            quarterly = self._compute_quarterly(items)

            results.append(PriceCategoryAnalysis(
                price_category_id=cat_id,
                price_category_code=cat.code,
                price_category_name=cat.name,
                material_group_id=cat.material_group_id,
                material_group_name=group.name if group else None,
                shape=cat.shape,
                total_po_lines=len(items),
                total_qty_received_kg=round(total_qty, 2),
                total_cost_czk=round(total_cost, 2),
                weighted_avg_price_per_kg=round(weighted_avg, 2),
                min_unit_price=round(min(unit_prices), 2) if unit_prices else 0.0,
                max_unit_price=round(max(unit_prices), 2) if unit_prices else 0.0,
                unique_vendors=len(vendor_counts),
                top_vendors=top_vendors,
                tiers=tier_analyses,
                weight_distribution=weight_dist,
                quarterly_prices=quarterly,
            ))

        # Sort by total_cost descending (most significant categories first)
        results.sort(key=lambda r: -r.total_cost_czk)
        return results

    def _analyze_tiers(
        self,
        items: List[Dict[str, Any]],
        tiers_db: List[MaterialPriceTier],
    ) -> List[TierAnalysis]:
        """Segment PO items into tier weight ranges and compute REAL averages per tier."""
        if not tiers_db:
            return []

        tier_results: List[TierAnalysis] = []

        for tier in tiers_db:
            min_w = tier.min_weight
            max_w = tier.max_weight  # None = infinity

            # Filter items that fall into this tier's weight range
            tier_items = [
                i for i in items
                if i["qty_received"] >= min_w
                and (max_w is None or i["qty_received"] < max_w)
            ]

            tier_qty = sum(i["qty_received"] for i in tier_items)
            tier_cost = sum(i["total_cost"] for i in tier_items)
            tier_avg = tier_cost / tier_qty if tier_qty > 0 else 0.0
            tier_prices = [i["unit_price"] for i in tier_items]

            # Compare with current DB price
            current = tier.price_per_kg
            diff_pct = None
            if current and current > 0 and tier_avg > 0:
                diff_pct = round(((tier_avg - current) / current) * 100, 1)

            label_max = f"{max_w:.0f}" if max_w is not None else "∞"
            tier_results.append(TierAnalysis(
                tier_id=tier.id,
                tier_label=f"{min_w:.0f}-{label_max} kg",
                min_weight=min_w,
                max_weight=max_w,
                avg_price_per_kg=round(tier_avg, 2),
                total_qty_kg=round(tier_qty, 2),
                total_cost_czk=round(tier_cost, 2),
                po_line_count=len(tier_items),
                min_price=round(min(tier_prices), 2) if tier_prices else 0.0,
                max_price=round(max(tier_prices), 2) if tier_prices else 0.0,
                current_price=current,
                current_tier_version=tier.version,
                diff_pct=diff_pct,
                sufficient_data=len(tier_items) >= 3,
            ))

        return tier_results

    # ── Distribution ─────────────────────────────────────────────

    @staticmethod
    def _compute_distribution(
        sorted_qtys: List[float],
        tiers_db: List[MaterialPriceTier],
    ) -> WeightDistribution:
        """Compute percentile-based weight distribution with suggested tier boundaries.

        Suggests new boundaries based on natural data breaks:
        - Tier 1→2 boundary at P33 (bottom third of purchases)
        - Tier 2→3 boundary at P67 (top third = bulk purchases)
        - Rounds to nice numbers (5, 10, 25, 50, 100 kg steps)
        """
        n = len(sorted_qtys)

        def percentile(pct: float) -> float:
            k = (n - 1) * pct / 100.0
            f = int(k)
            c = f + 1
            if c >= n:
                return sorted_qtys[-1]
            return sorted_qtys[f] + (k - f) * (sorted_qtys[c] - sorted_qtys[f])

        p25 = round(percentile(25), 2)
        p50 = round(percentile(50), 2)
        p75 = round(percentile(75), 2)

        # Suggest tier boundaries from data distribution
        suggestions: List[SuggestedBoundary] = []
        if len(tiers_db) >= 2:
            # For 3 tiers: split at P33 and P67 (equal data in each tier)
            raw_b1 = percentile(33) if len(tiers_db) >= 3 else percentile(50)
            raw_b2 = percentile(67) if len(tiers_db) >= 3 else None

            def round_boundary(val: float) -> float:
                """Round to nice weight boundary."""
                if val <= 5:
                    return round(val)
                if val <= 20:
                    return round(val / 5) * 5
                if val <= 100:
                    return round(val / 10) * 10
                if val <= 500:
                    return round(val / 25) * 25
                return round(val / 50) * 50

            nice_b1 = round_boundary(raw_b1)
            # Ensure minimum separation (at least 5 kg between boundaries)
            if nice_b1 < 1:
                nice_b1 = 5.0

            current_b1 = tiers_db[0].max_weight
            if nice_b1 != current_b1:
                suggestions.append(SuggestedBoundary(
                    tier_index=0,
                    current_max_weight=current_b1,
                    suggested_max_weight=nice_b1,
                    reason=f"P33={raw_b1:.0f}kg → zaokrouhleno na {nice_b1:.0f}kg",
                ))

            if raw_b2 is not None and len(tiers_db) >= 3:
                nice_b2 = round_boundary(raw_b2)
                if nice_b2 <= nice_b1:
                    nice_b2 = nice_b1 + (10 if nice_b1 < 100 else 50)
                current_b2 = tiers_db[1].max_weight
                if nice_b2 != current_b2:
                    suggestions.append(SuggestedBoundary(
                        tier_index=1,
                        current_max_weight=current_b2,
                        suggested_max_weight=nice_b2,
                        reason=f"P67={raw_b2:.0f}kg → zaokrouhleno na {nice_b2:.0f}kg",
                    ))

        return WeightDistribution(
            p25=p25,
            p50=p50,
            p75=p75,
            min_qty=round(sorted_qtys[0], 2),
            max_qty=round(sorted_qtys[-1], 2),
            avg_qty=round(sum(sorted_qtys) / n, 2),
            sample_count=n,
            suggested_boundaries=suggestions,
        )

    # ── Quarterly breakdown ──────────────────────────────────────

    @staticmethod
    def _compute_quarterly(items: List[Dict[str, Any]]) -> Dict[str, float]:
        """Compute weighted avg price per quarter (YYYY-QN)."""
        q_qty: Dict[str, float] = defaultdict(float)
        q_cost: Dict[str, float] = defaultdict(float)

        for item in items:
            date_str = item.get("order_date", "")
            if not date_str or len(date_str) < 8:
                continue
            # Format: "20260203 00:00:00.000" or "2026-02-03"
            clean = date_str.replace("-", "").replace(" ", "")[:8]
            try:
                year = int(clean[:4])
                month = int(clean[4:6])
            except (ValueError, IndexError):
                continue

            quarter = (month - 1) // 3 + 1
            key = f"{year}-Q{quarter}"
            q_qty[key] += item["qty_received"]
            q_cost[key] += item["total_cost"]

        result = {}
        for key in sorted(q_qty.keys()):
            if q_qty[key] > 0:
                result[key] = round(q_cost[key] / q_qty[key], 2)

        return result

    # ── Unmatched summary ────────────────────────────────────────

    @staticmethod
    def _summarize_unmatched(unmatched: List[Dict[str, Any]]) -> List[UnmatchedItem]:
        """Group unmatched items by (Item, reason) for compact display."""
        groups: Dict[Tuple[str, str], Dict[str, Any]] = {}

        for row in unmatched:
            item = str(row.get("Item", ""))
            reason = row.get("_reason", "Unknown")
            key = (item, reason)
            if key not in groups:
                groups[key] = {
                    "item": item,
                    "description": str(row.get("Description", "")),
                    "w_nr": None,
                    "reason": reason,
                    "total_cost": 0.0,
                    "count": 0,
                }
                # Try to extract W.Nr even for unmatched
                w_nr_match = MaterialImporter().extract_w_nr_from_item_code(item)
                if w_nr_match:
                    groups[key]["w_nr"] = w_nr_match

            total_cost = 0.0
            try:
                total_cost = float(row.get("DerTotalRcvdCost", 0))
            except (ValueError, TypeError):
                pass
            groups[key]["total_cost"] += total_cost
            groups[key]["count"] += 1

        result = [
            UnmatchedItem(
                item=g["item"],
                description=g["description"],
                w_nr=g["w_nr"],
                reason=g["reason"],
                total_cost=round(g["total_cost"], 2),
                count=g["count"],
            )
            for g in sorted(groups.values(), key=lambda x: -x["total_cost"])
        ]
        return result

    # ── Utilities ────────────────────────────────────────────────

    @staticmethod
    def _to_float(value: Any) -> float:
        """Safely convert Infor value to float."""
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
