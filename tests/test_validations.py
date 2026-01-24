"""Testy pro business validace v Pydantic modelech"""

import pytest
from pydantic import ValidationError


class TestPartValidations:
    """Testy validací pro Part model"""

    def test_part_number_required(self):
        """part_number je povinný"""
        from app.models.part import PartCreate
        with pytest.raises(ValidationError) as exc_info:
            PartCreate(material_item_id=1)
        assert "part_number" in str(exc_info.value)

    def test_part_number_min_length(self):
        """part_number musí mít alespoň 1 znak"""
        from app.models.part import PartCreate
        with pytest.raises(ValidationError) as exc_info:
            PartCreate(part_number="", material_item_id=1)
        assert "part_number" in str(exc_info.value)

    def test_part_number_max_length(self):
        """part_number max 50 znaků"""
        from app.models.part import PartCreate
        with pytest.raises(ValidationError) as exc_info:
            PartCreate(part_number="x" * 51, material_item_id=1)
        assert "part_number" in str(exc_info.value)

    def test_part_length_non_negative(self):
        """length nesmí být záporná"""
        from app.models.part import PartCreate
        with pytest.raises(ValidationError) as exc_info:
            PartCreate(part_number="TEST-001", material_item_id=1, length=-5)
        assert "length" in str(exc_info.value)

    def test_part_valid_data(self):
        """Validní data projdou"""
        from app.models.part import PartCreate
        part = PartCreate(
            part_number="TEST-001",
            material_item_id=1,
            length=100.0,
            name="Test díl"
        )
        assert part.part_number == "TEST-001"
        assert part.length == 100.0


class TestBatchValidations:
    """Testy validací pro Batch model"""

    def test_batch_quantity_positive(self):
        """quantity musí být > 0"""
        from app.models.batch import BatchCreate
        with pytest.raises(ValidationError) as exc_info:
            BatchCreate(part_id=1, quantity=0)
        assert "quantity" in str(exc_info.value)

    def test_batch_quantity_negative(self):
        """quantity nesmí být záporná"""
        from app.models.batch import BatchCreate
        with pytest.raises(ValidationError) as exc_info:
            BatchCreate(part_id=1, quantity=-5)
        assert "quantity" in str(exc_info.value)

    def test_batch_valid_data(self):
        """Validní data projdou"""
        from app.models.batch import BatchCreate
        batch = BatchCreate(part_id=1, quantity=100)
        assert batch.quantity == 100


class TestFeatureValidations:
    """Testy validací pro Feature model"""

    def test_feature_count_positive(self):
        """count musí být >= 1"""
        from app.models.feature import FeatureCreate
        with pytest.raises(ValidationError) as exc_info:
            FeatureCreate(operation_id=1, count=0)
        assert "count" in str(exc_info.value)

    def test_feature_blade_width_positive(self):
        """blade_width musí být > 0"""
        from app.models.feature import FeatureCreate
        with pytest.raises(ValidationError) as exc_info:
            FeatureCreate(operation_id=1, blade_width=0)
        assert "blade_width" in str(exc_info.value)

    def test_feature_diameter_non_negative(self):
        """from_diameter nesmí být záporný"""
        from app.models.feature import FeatureCreate
        with pytest.raises(ValidationError) as exc_info:
            FeatureCreate(operation_id=1, from_diameter=-10)
        assert "from_diameter" in str(exc_info.value)

    def test_feature_length_non_negative(self):
        """length nesmí být záporná"""
        from app.models.feature import FeatureCreate
        with pytest.raises(ValidationError) as exc_info:
            FeatureCreate(operation_id=1, length=-5)
        assert "length" in str(exc_info.value)

    def test_feature_valid_data(self):
        """Validní data projdou"""
        from app.models.feature import FeatureCreate
        feature = FeatureCreate(
            operation_id=1,
            from_diameter=20,
            to_diameter=18,
            length=50,
            count=2
        )
        assert feature.from_diameter == 20
        assert feature.count == 2


class TestOperationValidations:
    """Testy validací pro Operation model"""

    def test_operation_seq_positive(self):
        """seq musí být >= 1"""
        from app.models.operation import OperationCreate
        with pytest.raises(ValidationError) as exc_info:
            OperationCreate(part_id=1, seq=0)
        assert "seq" in str(exc_info.value)

    def test_operation_setup_time_non_negative(self):
        """setup_time_min nesmí být záporný"""
        from app.models.operation import OperationCreate
        with pytest.raises(ValidationError) as exc_info:
            OperationCreate(part_id=1, setup_time_min=-10)
        assert "setup_time_min" in str(exc_info.value)

    def test_operation_coop_price_non_negative(self):
        """coop_price nesmí být záporná"""
        from app.models.operation import OperationCreate
        with pytest.raises(ValidationError) as exc_info:
            OperationCreate(part_id=1, coop_price=-100)
        assert "coop_price" in str(exc_info.value)

    def test_operation_coop_days_non_negative(self):
        """coop_days nesmí být záporný"""
        from app.models.operation import OperationCreate
        with pytest.raises(ValidationError) as exc_info:
            OperationCreate(part_id=1, coop_days=-5)
        assert "coop_days" in str(exc_info.value)

    def test_operation_valid_data(self):
        """Validní data projdou"""
        from app.models.operation import OperationCreate
        op = OperationCreate(
            part_id=1,
            seq=10,
            name="Soustružení",
            setup_time_min=30
        )
        assert op.seq == 10
        assert op.setup_time_min == 30


class TestMaterialValidations:
    """Testy validací pro Material modely (již existující)"""

    def test_material_group_density_positive(self):
        """density musí být > 0"""
        from app.models.material import MaterialGroupCreate
        with pytest.raises(ValidationError) as exc_info:
            MaterialGroupCreate(code="TEST", name="Test", density=0)
        assert "density" in str(exc_info.value)

    def test_material_item_price_positive(self):
        """price_per_kg musí být > 0"""
        from app.models.material import MaterialItemCreate
        from app.models.enums import StockShape
        with pytest.raises(ValidationError) as exc_info:
            MaterialItemCreate(
                code="TEST",
                name="Test",
                shape=StockShape.ROUND_BAR,
                price_per_kg=0,
                material_group_id=1
            )
        assert "price_per_kg" in str(exc_info.value)
