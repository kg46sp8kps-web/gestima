#!/usr/bin/env python3
"""Seed kompletního demo dílu s operacemi a batches"""
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.database import async_session
from app.models import Part, Operation, Batch, MachineDB, MaterialItem, MaterialGroup
from sqlalchemy import select
from datetime import datetime
from app.services.price_calculator import calculate_batch_prices, calculate_stock_cost_from_part


async def seed():
    print("🌱 Seed kompletního demo dílu\n" + "=" * 80)

    async with async_session() as db:
        # 1. Načti materiál
        from sqlalchemy.orm import selectinload as si
        material = (await db.execute(
            select(MaterialItem)
            .options(si(MaterialItem.group), si(MaterialItem.price_category))
            .where(MaterialItem.deleted_at.is_(None))
            .limit(1)
        )).scalar_one_or_none()
        if not material:
            print("❌ Chybí materiály. Spusť: python -m scripts.seed_materials")
            return

        material_group = material.group
        price_category = material.price_category
        print(f"✅ Materiál: {material.code} (kategorie: {price_category.code}, hustota: {material_group.density} kg/dm³)")

        # 2. Načti stroje
        machines = (await db.execute(select(MachineDB).where(MachineDB.deleted_at.is_(None), MachineDB.active == True))).scalars().all()
        if not machines:
            print("❌ Chybí stroje. Spusť: ./venv/bin/python scripts/seed_machines.py")
            return

        lathe = next((m for m in machines if m.type == 'lathe'), machines[0])
        mill = next((m for m in machines if m.type == 'mill'), None)
        print(f"✅ Soustruh: {lathe.code} ({lathe.hourly_rate_operation} Kč/h)")
        if mill:
            print(f"✅ Frézka: {mill.code} ({mill.hourly_rate_operation} Kč/h)")

        # 3. Vytvoř díl
        part = Part(
            part_number="DEMO-COMPLETE",
            article_number="ART-COMPLETE",
            name="Demo hřídel - kompletní",
            material_item_id=material.id,
            stock_diameter=40.0,
            stock_length=100.0,
            length=85.0,
            notes="Kompletní demo díl pro testování",
            created_by="seed",
            updated_by="seed"
        )
        db.add(part)
        await db.flush()
        print(f"\n✅ Díl #{part.id}: {part.part_number}")
        print(f"   Stock: Ø{part.stock_diameter} × {part.stock_length}mm")

        # 4. Operace
        op1 = Operation(
            part_id=part.id, seq=10, name="Soustružení", type="turning", icon="⚙️",
            machine_id=lathe.id, cutting_mode="MID",
            setup_time_min=15.0, operation_time_min=8.5,
            is_coop=False, created_by="seed", updated_by="seed"
        )
        db.add(op1)
        print(f"   ✅ Op #{op1.seq}: {op1.name} (tp={op1.operation_time_min}, tj={op1.setup_time_min})")

        if mill:
            op2 = Operation(
                part_id=part.id, seq=20, name="Frézování", type="milling", icon="🔧",
                machine_id=mill.id, cutting_mode="MID",
                setup_time_min=10.0, operation_time_min=5.0,
                is_coop=False, created_by="seed", updated_by="seed"
            )
            db.add(op2)
            print(f"   ✅ Op #{op2.seq}: {op2.name} (tp={op2.operation_time_min}, tj={op2.setup_time_min})")

        await db.flush()

        # 5. Načti part s relacemi pro výpočet
        from sqlalchemy.orm import selectinload
        part_with_relations = (await db.execute(
            select(Part)
            .where(Part.id == part.id)
            .options(
                selectinload(Part.material_item).selectinload(MaterialItem.group),
                selectinload(Part.material_item).selectinload(MaterialItem.price_category)
            )
        )).scalar_one()

        # 6. Připrav data pro batch výpočty
        operations_list = [
            {"machine_id": lathe.id, "operation_time_min": 8.5, "setup_time_min": 15.0, "is_coop": False}
        ]
        machines_dict = {lathe.id: {"hourly_rate": lathe.hourly_rate_operation}}

        if mill:
            operations_list.append({"machine_id": mill.id, "operation_time_min": 5.0, "setup_time_min": 10.0, "is_coop": False})
            machines_dict[mill.id] = {"hourly_rate": mill.hourly_rate_operation}

        # 7. Batche (ADR-014: material cost depends on quantity → compute for each batch)
        print(f"\n📦 Batche:")
        for quantity, is_default in [(1, True), (10, False), (100, False)]:
            # Vypočti material cost pro tento batch (price tier depends on quantity)
            stock_cost_result = await calculate_stock_cost_from_part(part_with_relations, quantity, db)
            material_cost = stock_cost_result.cost
            price_per_kg = stock_cost_result.price_per_kg

            prices = calculate_batch_prices(quantity, material_cost, operations_list, machines_dict)
            # Vypočti total time (tp + tj/qty) pro všechny operace
            total_time = sum(op["operation_time_min"] + (op["setup_time_min"] / quantity) for op in operations_list)

            batch = Batch(
                part_id=part.id, quantity=quantity, is_default=is_default,
                unit_time_min=round(total_time, 2),
                material_cost=prices.material_cost,
                machining_cost=prices.machining_cost,
                setup_cost=prices.setup_cost,
                coop_cost=prices.coop_cost,
                unit_cost=prices.unit_cost,
                total_cost=prices.total_cost,
                is_frozen=False, created_by="seed", updated_by="seed"
            )
            db.add(batch)
            total_weight_kg = stock_cost_result.weight_kg * quantity
            print(f"   ✅ {quantity:3d} ks: {batch.unit_cost:7.2f} Kč/ks (mat: {batch.material_cost:.2f} @ {price_per_kg:.1f} Kč/kg, váha: {total_weight_kg:.1f}kg)")

        await db.commit()

        print(f"\n{'=' * 80}")
        print(f"✅ HOTOVO! URL: http://localhost:8000/parts/{part.id}/edit")
        print(f"\n🧪 Test checklist:")
        print(f"   [ ] Stock rozměry zobrazeny")
        print(f"   [ ] Operace se stroji zobrazeny")
        print(f"   [ ] Cenová tabulka s bar charty")
        print(f"   [ ] Modal 📊 Detail")


if __name__ == "__main__":
    asyncio.run(seed())
