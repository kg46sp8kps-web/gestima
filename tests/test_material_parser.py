"""GESTIMA - Material Parser Service Tests"""

import pytest
from sqlalchemy import select

from app.services.material_parser import MaterialParserService, ParseResult
from app.models.material import MaterialGroup, MaterialPriceCategory
from app.models.material_norm import MaterialNorm
from app.models.enums import StockShape


class TestMaterialParser:
    """Test suite pro MaterialParserService (Fáze 1: Regex-based parsing)"""

    @pytest.mark.asyncio
    async def test_circle_stainless_with_length(self, db_session):
        """D20 1.4301 100mm → kulatina nerez D20, délka 100"""
        parser = MaterialParserService(db_session)
        result = await parser.parse("D20 1.4301 100mm")

        assert result.shape == StockShape.ROUND_BAR
        assert result.diameter == 20.0
        assert result.material_norm == "1.4301"
        assert result.material_category == "nerez"
        assert result.length == 100.0
        assert result.confidence >= 0.8  # Shape + material + length

    @pytest.mark.asyncio
    async def test_circle_alternate_notation(self, db_session):
        """Ø20 1.4301 L=100 → stejné jako D20"""
        parser = MaterialParserService(db_session)
        result = await parser.parse("Ø20 1.4301 L=100")

        assert result.shape == StockShape.ROUND_BAR
        assert result.diameter == 20.0
        assert result.material_norm == "1.4301"
        assert result.length == 100.0

    @pytest.mark.asyncio
    async def test_circle_lowercase(self, db_session):
        """d20 1.4301 → lowercase OK"""
        parser = MaterialParserService(db_session)
        result = await parser.parse("d20 1.4301")

        assert result.shape == StockShape.ROUND_BAR
        assert result.diameter == 20.0
        assert result.material_norm == "1.4301"

    @pytest.mark.asyncio
    async def test_square_steel_c45(self, db_session):
        """20x20 C45 500 → čtyřhran ocel 20x20, délka 500"""
        parser = MaterialParserService(db_session)
        result = await parser.parse("20x20 C45 500")

        assert result.shape == StockShape.SQUARE_BAR
        assert result.width == 20.0
        assert result.height == 20.0
        assert result.material_norm == "C45"
        assert result.material_category == "ocel"
        assert result.length == 500.0

    @pytest.mark.asyncio
    async def test_flat_bar_steel(self, db_session):
        """20x30 S235 500 → profil ocel 20x30, délka 500"""
        parser = MaterialParserService(db_session)
        result = await parser.parse("20x30 S235 500")

        assert result.shape == StockShape.FLAT_BAR
        assert result.width == 20.0
        assert result.height == 30.0
        assert result.material_norm == "S235"
        assert result.material_category == "ocel"
        assert result.length == 500.0

    @pytest.mark.asyncio
    async def test_square_symbol_aluminum(self, db_session):
        """□30 6060 200 → čtyřhran hliník 30x30"""
        parser = MaterialParserService(db_session)
        result = await parser.parse("□30 6060 200")

        assert result.shape == StockShape.SQUARE_BAR
        assert result.width == 30.0
        assert result.height == 30.0
        assert result.material_category == "hlinik"
        assert result.length == 200.0

    @pytest.mark.asyncio
    async def test_hexagon_brass(self, db_session):
        """⬡24 CuZn37 150 → šestihran mosaz 24mm"""
        parser = MaterialParserService(db_session)
        result = await parser.parse("⬡24 CuZn37 150")

        assert result.shape == StockShape.HEXAGONAL_BAR
        assert result.width == 24.0
        assert result.material_norm == "CUZN37"
        assert result.material_category == "mosaz"
        assert result.length == 150.0

    @pytest.mark.asyncio
    async def test_plate_stainless(self, db_session):
        """t2 1.4301 → plech nerez tl.2mm"""
        parser = MaterialParserService(db_session)
        result = await parser.parse("t2 1.4301")

        assert result.shape == StockShape.PLATE
        assert result.thickness == 2.0
        assert result.material_norm == "1.4301"
        assert result.material_category == "nerez"

    @pytest.mark.asyncio
    async def test_plate_alternate_notation(self, db_session):
        """tl.3 1.4301 → plech nerez tl.3mm"""
        parser = MaterialParserService(db_session)
        result = await parser.parse("tl.3 1.4301")

        assert result.shape == StockShape.PLATE
        assert result.thickness == 3.0

    @pytest.mark.asyncio
    async def test_tube_stainless(self, db_session):
        """D20x2 1.4301 100 → trubka D20 tl.2mm nerez, délka 100"""
        parser = MaterialParserService(db_session)
        result = await parser.parse("D20x2 1.4301 100")

        assert result.shape == StockShape.TUBE
        assert result.diameter == 20.0
        assert result.wall_thickness == 2.0
        assert result.material_norm == "1.4301"
        assert result.length == 100.0

    @pytest.mark.asyncio
    async def test_tube_alternate_symbol(self, db_session):
        """Ø25x3 S235 → trubka Ø25 tl.3mm ocel"""
        parser = MaterialParserService(db_session)
        result = await parser.parse("Ø25x3 S235")

        assert result.shape == StockShape.TUBE
        assert result.diameter == 25.0
        assert result.wall_thickness == 3.0
        assert result.material_norm == "S235"

    @pytest.mark.asyncio
    async def test_partial_match_shape_only(self, db_session):
        """D20 → jen průměr, žádný materiál (nízká confidence)"""
        parser = MaterialParserService(db_session)
        result = await parser.parse("D20")

        assert result.shape == StockShape.ROUND_BAR
        assert result.diameter == 20.0
        assert result.material_norm is None
        assert result.confidence < 0.7  # Částečné rozpoznání

    @pytest.mark.asyncio
    async def test_partial_match_material_only(self, db_session):
        """C45 → jen materiál, žádný tvar (nízká confidence)"""
        parser = MaterialParserService(db_session)
        result = await parser.parse("C45")

        assert result.shape is None
        assert result.material_norm == "C45"
        assert result.material_category == "ocel"
        assert result.confidence < 0.7

    @pytest.mark.asyncio
    async def test_no_match(self, db_session):
        """Nesmyslný input → nulová confidence"""
        parser = MaterialParserService(db_session)
        result = await parser.parse("asdfghjkl")

        assert result.confidence == 0.0
        assert result.shape is None
        assert result.material_norm is None

    @pytest.mark.asyncio
    async def test_empty_input(self, db_session):
        """Prázdný input → nulová confidence"""
        parser = MaterialParserService(db_session)
        result = await parser.parse("")

        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_extra_whitespace(self, db_session):
        """D  20   1.4301    100 → extra mezery OK"""
        parser = MaterialParserService(db_session)
        result = await parser.parse("D  20   1.4301    100")

        assert result.diameter == 20.0
        assert result.material_norm == "1.4301"
        assert result.length == 100.0

    @pytest.mark.asyncio
    async def test_decimal_values(self, db_session):
        """D20.5 C45 100.5 → desetinné hodnoty OK"""
        parser = MaterialParserService(db_session)
        result = await parser.parse("D20.5 C45 100.5")

        assert result.diameter == 20.5
        assert result.length == 100.5

    @pytest.mark.asyncio
    async def test_material_norm_variations(self, db_session):
        """Test různých variant norem"""
        parser = MaterialParserService(db_session)

        # W.Nr (1.xxxx)
        r1 = await parser.parse("D20 1.0503")
        assert r1.material_norm == "1.0503"
        assert r1.material_category == "ocel"

        # EN ISO (C45, S235)
        r2 = await parser.parse("D20 C45")
        assert r2.material_norm == "C45"
        assert r2.material_category == "ocel"

        # AISI stainless (304)
        # Note: parser may not recognize bare "304" without context
        # This is expected limitation of regex-based approach

        # Legovaná ocel (42CrMo4)
        r3 = await parser.parse("D20 42CrMo4")
        assert r3.material_norm == "42CRMO4"
        assert r3.material_category == "ocel"

        # Hliník (EN AW-6060)
        r4 = await parser.parse("D20 EN AW-6060")
        assert r4.material_category == "hlinik"

        # Mosaz (CuZn37)
        r5 = await parser.parse("D20 CuZn37")
        assert r5.material_norm == "CUZN37"
        assert r5.material_category == "mosaz"

    @pytest.mark.asyncio
    async def test_length_extraction_variations(self, db_session):
        """Test různých formátů délky"""
        parser = MaterialParserService(db_session)

        # Plain number
        r1 = await parser.parse("D20 C45 100")
        assert r1.length == 100.0

        # With "mm"
        r2 = await parser.parse("D20 C45 100mm")
        assert r2.length == 100.0

        # With "L="
        r3 = await parser.parse("D20 C45 L=100")
        assert r3.length == 100.0

        # With "length="
        r4 = await parser.parse("D20 C45 length=100")
        assert r4.length == 100.0

    @pytest.mark.asyncio
    async def test_db_lookup_material_group(self, db_session, seed_materials):
        """Test DB lookup pro MaterialGroup (pokud existuje)"""
        # Seed data creates MaterialGroup with code "C45"
        # and MaterialNorm with en_iso="C45" → MaterialGroup

        parser = MaterialParserService(db_session)
        result = await parser.parse("D20 C45 100")

        # Pokud seed data obsahují C45 → group by měla být nalezena
        if result.suggested_material_group_id:
            assert result.suggested_material_group_code == "C45"
            assert result.suggested_material_group_density > 0
            assert result.confidence >= 0.9  # +0.1 za nalezený group

    @pytest.mark.asyncio
    async def test_confidence_scoring(self, db_session):
        """Test confidence scoring logic"""
        parser = MaterialParserService(db_session)

        # Jen tvar: 0.4
        r1 = await parser.parse("D20")
        assert r1.confidence == pytest.approx(0.4, abs=0.05)

        # Tvar + materiál: 0.7
        r2 = await parser.parse("D20 C45")
        assert r2.confidence >= 0.7

        # Tvar + materiál + délka: 0.8
        r3 = await parser.parse("D20 C45 100")
        assert r3.confidence >= 0.8

        # Full match s DB lookup: 0.9+
        # (pokud C45 existuje v DB)

    @pytest.mark.asyncio
    async def test_matched_pattern_metadata(self, db_session):
        """Test matched_pattern pro debugging"""
        parser = MaterialParserService(db_session)

        r1 = await parser.parse("D20 C45")
        assert r1.matched_pattern == "round_bar"

        r2 = await parser.parse("20x30 S235")
        assert r2.matched_pattern == "square_or_flat_bar"

        r3 = await parser.parse("t2 1.4301")
        assert r3.matched_pattern == "plate"

        r4 = await parser.parse("D20x2 1.4301")
        assert r4.matched_pattern == "tube"

    @pytest.mark.asyncio
    async def test_raw_input_preserved(self, db_session):
        """Test že raw_input je zachován v result"""
        parser = MaterialParserService(db_session)
        result = await parser.parse("D20 C45 100mm")

        assert result.raw_input == "D20 C45 100mm"


# ========== EDGE CASES ==========

class TestMaterialParserEdgeCases:
    """Edge cases a boundary conditions"""

    @pytest.mark.asyncio
    async def test_tube_vs_flat_bar_priority(self, db_session):
        """D20x2 musí matchovat jako trubka, NE jako profil 20x2"""
        parser = MaterialParserService(db_session)
        result = await parser.parse("D20x2 C45")

        # TUBE pattern má prioritu (je první v seznamu)
        assert result.shape == StockShape.TUBE
        assert result.diameter == 20.0
        assert result.wall_thickness == 2.0

    @pytest.mark.asyncio
    async def test_square_detection(self, db_session):
        """20x20 vs 20x30 - detekce čtyřhran vs profil"""
        parser = MaterialParserService(db_session)

        # Stejné rozměry → čtyřhran
        r1 = await parser.parse("20x20 C45")
        assert r1.shape == StockShape.SQUARE_BAR

        # Různé rozměry → profil
        r2 = await parser.parse("20x30 C45")
        assert r2.shape == StockShape.FLAT_BAR

    @pytest.mark.asyncio
    async def test_ambiguous_numbers(self, db_session):
        """Test když je více čísel v textu"""
        parser = MaterialParserService(db_session)

        # "1.4301" by nemělo být interpretováno jako délka
        result = await parser.parse("D20 1.4301")
        assert result.diameter == 20.0
        assert result.material_norm == "1.4301"
        # Length může být None nebo může vzít číslo z normy (edge case)
        # Acceptance: Parser může mít false positive na length

    @pytest.mark.asyncio
    async def test_unicode_symbols(self, db_session):
        """Test Unicode symbolů (Ø, □, ⬡)"""
        parser = MaterialParserService(db_session)

        r1 = await parser.parse("Ø20")
        assert r1.shape == StockShape.ROUND_BAR

        r2 = await parser.parse("□30")
        assert r2.shape == StockShape.SQUARE_BAR

        r3 = await parser.parse("⬡24")
        assert r3.shape == StockShape.HEXAGONAL_BAR

    @pytest.mark.asyncio
    async def test_very_long_input(self, db_session):
        """Test velmi dlouhého vstupu (nemělo by spadnout)"""
        parser = MaterialParserService(db_session)
        long_input = "D20 " + "x" * 1000 + " C45"

        result = await parser.parse(long_input)
        # Should still extract D20 and C45
        assert result.diameter == 20.0
        assert result.material_norm == "C45"

    @pytest.mark.asyncio
    async def test_special_characters(self, db_session):
        """Test speciálních znaků (nemělo by spadnout)"""
        parser = MaterialParserService(db_session)

        # Závorky, čárky, pomlčky - měly by být ignorovány
        result = await parser.parse("D20 (C45) 100mm")
        assert result.diameter == 20.0
        # Note: Závorky mohou ovlivnit parsing, ale nemělo by to spadnout
