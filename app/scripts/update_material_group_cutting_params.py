#!/usr/bin/env python3
"""
Update existing material groups (8-digit codes) with cutting parameters.

This script updates the material_groups table with cutting parameters
based on real-world data from tool manufacturers (Iscar, Sandvik, Kennametal).

Usage:
    python app/scripts/update_material_group_cutting_params.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.models.material import MaterialGroup


# Cutting parameters mapped to 8-digit material codes
CUTTING_PARAMS = {
    "20910000": {  # Hliník
        "iso_group": "N",
        "hardness_hb": 80.0,
        "mrr_turning_roughing": 1200.0,
        "mrr_turning_finishing": 300.0,
        "mrr_milling_roughing": 800.0,
        "mrr_milling_finishing": 200.0,
        "cutting_speed_turning": 350.0,
        "cutting_speed_milling": 300.0,
        "feed_turning": 0.35,
        "feed_milling": 0.25,
        "deep_pocket_penalty": 1.5,
        "thin_wall_penalty": 2.0,
        "cutting_data_source": "Iscar 2024 / Sandvik Coromant 2024",
    },
    "20910001": {  # Měď
        "iso_group": "N",
        "hardness_hb": 90.0,
        "mrr_turning_roughing": 800.0,
        "mrr_turning_finishing": 200.0,
        "mrr_milling_roughing": 500.0,
        "mrr_milling_finishing": 125.0,
        "cutting_speed_turning": 200.0,
        "cutting_speed_milling": 180.0,
        "feed_turning": 0.30,
        "feed_milling": 0.20,
        "deep_pocket_penalty": 1.6,
        "thin_wall_penalty": 2.2,
        "cutting_data_source": "Kennametal 2024",
    },
    "20910002": {  # Mosaz
        "iso_group": "N",
        "hardness_hb": 100.0,
        "mrr_turning_roughing": 1000.0,
        "mrr_turning_finishing": 250.0,
        "mrr_milling_roughing": 650.0,
        "mrr_milling_finishing": 160.0,
        "cutting_speed_turning": 250.0,
        "cutting_speed_milling": 220.0,
        "feed_turning": 0.32,
        "feed_milling": 0.22,
        "deep_pocket_penalty": 1.5,
        "thin_wall_penalty": 2.0,
        "cutting_data_source": "Sandvik Coromant 2024",
    },
    "20910003": {  # Ocel automatová
        "iso_group": "P",
        "hardness_hb": 180.0,
        "mrr_turning_roughing": 450.0,
        "mrr_turning_finishing": 110.0,
        "mrr_milling_roughing": 300.0,
        "mrr_milling_finishing": 75.0,
        "cutting_speed_turning": 220.0,
        "cutting_speed_milling": 200.0,
        "feed_turning": 0.28,
        "feed_milling": 0.18,
        "deep_pocket_penalty": 1.8,
        "thin_wall_penalty": 2.5,
        "cutting_data_source": "Iscar 2024 (11SM, 11SMn30)",
    },
    "20910004": {  # Ocel konstrukční
        "iso_group": "P",
        "hardness_hb": 200.0,
        "mrr_turning_roughing": 400.0,
        "mrr_turning_finishing": 100.0,
        "mrr_milling_roughing": 250.0,
        "mrr_milling_finishing": 65.0,
        "cutting_speed_turning": 180.0,
        "cutting_speed_milling": 160.0,
        "feed_turning": 0.25,
        "feed_milling": 0.16,
        "deep_pocket_penalty": 1.8,
        "thin_wall_penalty": 2.5,
        "cutting_data_source": "Sandvik Coromant 2024 (C45, 16MnCr5)",
    },
    "20910005": {  # Ocel legovaná
        "iso_group": "P",
        "hardness_hb": 250.0,
        "mrr_turning_roughing": 300.0,
        "mrr_turning_finishing": 75.0,
        "mrr_milling_roughing": 180.0,
        "mrr_milling_finishing": 45.0,
        "cutting_speed_turning": 150.0,
        "cutting_speed_milling": 140.0,
        "feed_turning": 0.22,
        "feed_milling": 0.14,
        "deep_pocket_penalty": 2.0,
        "thin_wall_penalty": 2.8,
        "cutting_data_source": "Iscar 2024 (42CrMo4, 34CrNiMo6)",
    },
    "20910006": {  # Ocel nástrojová
        "iso_group": "K",
        "hardness_hb": 300.0,
        "mrr_turning_roughing": 200.0,
        "mrr_turning_finishing": 50.0,
        "mrr_milling_roughing": 120.0,
        "mrr_milling_finishing": 30.0,
        "cutting_speed_turning": 110.0,
        "cutting_speed_milling": 100.0,
        "feed_turning": 0.18,
        "feed_milling": 0.12,
        "deep_pocket_penalty": 2.2,
        "thin_wall_penalty": 3.0,
        "cutting_data_source": "Kennametal 2024 (X153CrMoV12, 90MnCrV8)",
    },
    "20910007": {  # Nerez
        "iso_group": "M",
        "hardness_hb": 220.0,
        "mrr_turning_roughing": 250.0,
        "mrr_turning_finishing": 65.0,
        "mrr_milling_roughing": 150.0,
        "mrr_milling_finishing": 40.0,
        "cutting_speed_turning": 130.0,
        "cutting_speed_milling": 120.0,
        "feed_turning": 0.20,
        "feed_milling": 0.14,
        "deep_pocket_penalty": 2.0,
        "thin_wall_penalty": 2.8,
        "cutting_data_source": "Sandvik Coromant 2024 (1.4301, 1.4401)",
    },
    "20910008": {  # Plasty
        "iso_group": "N",
        "hardness_hb": 30.0,
        "mrr_turning_roughing": 2000.0,
        "mrr_turning_finishing": 500.0,
        "mrr_milling_roughing": 1500.0,
        "mrr_milling_finishing": 400.0,
        "cutting_speed_turning": 500.0,
        "cutting_speed_milling": 450.0,
        "feed_turning": 0.40,
        "feed_milling": 0.30,
        "deep_pocket_penalty": 1.3,
        "thin_wall_penalty": 1.8,
        "cutting_data_source": "Kennametal 2024 (POM, PA6, PEEK)",
    },
}


def update_cutting_params(db: Session) -> None:
    """Update material groups with cutting parameters."""

    print("🔄 Updating material groups with cutting parameters...")
    print()

    updated_count = 0
    skipped_count = 0

    for code, params in CUTTING_PARAMS.items():
        material = db.query(MaterialGroup).filter(MaterialGroup.code == code).first()

        if not material:
            print(f"⚠️  Material {code} not found - skipping")
            skipped_count += 1
            continue

        # Update cutting parameters
        for key, value in params.items():
            setattr(material, key, value)

        print(f"✅ Updated {code} ({material.name})")
        print(f"   ISO: {params['iso_group']}, MRR Fréza: {params['mrr_milling_roughing']:.0f} cm³/min, Vc: {params['cutting_speed_milling']:.0f} m/min")

        updated_count += 1

    try:
        db.commit()
        print()
        print(f"✅ Successfully updated {updated_count} material groups")
        if skipped_count > 0:
            print(f"⚠️  Skipped {skipped_count} missing materials")
    except Exception as e:
        db.rollback()
        print()
        print(f"❌ Error updating materials: {e}")
        raise


def main() -> None:
    """Main entry point."""
    print("=" * 80)
    print("UPDATE MATERIAL GROUPS - Cutting Parameters")
    print("=" * 80)
    print()

    engine = create_engine('sqlite:///./gestima.db')
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        update_cutting_params(db)
    finally:
        db.close()

    print()
    print("=" * 80)
    print("Update complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
