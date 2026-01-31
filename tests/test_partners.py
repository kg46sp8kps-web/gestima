"""GESTIMA - Partners tests

Tests:
- CRUD operations
- ICO/DIC validation
- Filtering (is_customer/is_supplier)
- Partner number generation
- Search functionality
"""

import pytest
from httpx import AsyncClient
from app.models.partner import PartnerCreate, PartnerUpdate
from pydantic import ValidationError


@pytest.mark.asyncio
async def test_create_partner_auto_number(client: AsyncClient, admin_headers):
    """Test vytvoření partnera s auto-generovaným číslem (70XXXXXX)"""
    data = {
        "company_name": "Test Company s.r.o.",
        "ico": "27082440",  # Valid ICO (mod 11 checksum)
        "dic": "CZ27082440",
        "is_customer": True,
        "is_supplier": False
    }

    response = await client.post("/api/partners/", json=data, headers=admin_headers)
    assert response.status_code == 200

    partner = response.json()
    assert partner["partner_number"].startswith("70")
    assert len(partner["partner_number"]) == 8
    assert partner["company_name"] == "Test Company s.r.o."
    assert partner["ico"] == "27082440"
    assert partner["dic"] == "CZ27082440"
    assert partner["is_customer"] is True
    assert partner["is_supplier"] is False


@pytest.mark.asyncio
async def test_create_partner_custom_number(client: AsyncClient, admin_headers):
    """Test vytvoření partnera s vlastním číslem"""
    data = {
        "partner_number": "70999999",
        "company_name": "Custom Number s.r.o.",
        "is_customer": False,
        "is_supplier": True
    }

    response = await client.post("/api/partners/", json=data, headers=admin_headers)
    assert response.status_code == 200

    partner = response.json()
    assert partner["partner_number"] == "70999999"
    assert partner["is_customer"] is False
    assert partner["is_supplier"] is True


@pytest.mark.asyncio
async def test_create_partner_duplicate_number(client: AsyncClient, admin_headers):
    """Test zamezení duplicitního partner_number"""
    data1 = {
        "partner_number": "70888888",
        "company_name": "First Partner",
    }
    response1 = await client.post("/api/partners/", json=data1, headers=admin_headers)
    assert response1.status_code == 200

    # Duplicate
    data2 = {
        "partner_number": "70888888",
        "company_name": "Second Partner",
    }
    response2 = await client.post("/api/partners/", json=data2, headers=admin_headers)
    assert response2.status_code == 400
    assert "již existuje" in response2.json()["detail"]


@pytest.mark.asyncio
async def test_get_partner(client: AsyncClient, admin_headers):
    """Test získání partnera podle partner_number"""
    # Create
    data = {
        "company_name": "Get Test s.r.o.",
        "email": "test@example.com"
    }
    create_response = await client.post("/api/partners/", json=data, headers=admin_headers)
    partner_number = create_response.json()["partner_number"]

    # Get
    response = await client.get(f"/api/partners/{partner_number}", headers=admin_headers)
    assert response.status_code == 200

    partner = response.json()
    assert partner["partner_number"] == partner_number
    assert partner["company_name"] == "Get Test s.r.o."
    assert partner["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_update_partner(client: AsyncClient, admin_headers):
    """Test aktualizace partnera (optimistic locking)"""
    # Create
    data = {
        "company_name": "Update Test s.r.o.",
        "phone": "+420123456789"
    }
    create_response = await client.post("/api/partners/", json=data, headers=admin_headers)
    partner = create_response.json()
    partner_number = partner["partner_number"]
    version = partner["version"]

    # Update
    update_data = {
        "company_name": "Updated Name s.r.o.",
        "phone": "+420987654321",
        "version": version
    }
    response = await client.put(f"/api/partners/{partner_number}", json=update_data, headers=admin_headers)
    assert response.status_code == 200

    updated = response.json()
    assert updated["company_name"] == "Updated Name s.r.o."
    assert updated["phone"] == "+420987654321"
    assert updated["version"] == version + 1


@pytest.mark.asyncio
async def test_update_partner_version_conflict(client: AsyncClient, admin_headers):
    """Test optimistic locking - version conflict"""
    # Create
    data = {"company_name": "Version Test s.r.o."}
    create_response = await client.post("/api/partners/", json=data, headers=admin_headers)
    partner_number = create_response.json()["partner_number"]

    # Update with wrong version
    update_data = {
        "company_name": "Should Fail",
        "version": 999  # Wrong version
    }
    response = await client.put(f"/api/partners/{partner_number}", json=update_data, headers=admin_headers)
    assert response.status_code == 409
    assert "změněna jiným uživatelem" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_partner(client: AsyncClient, admin_headers):
    """Test smazání partnera"""
    # Create
    data = {"company_name": "Delete Test s.r.o."}
    create_response = await client.post("/api/partners/", json=data, headers=admin_headers)
    partner_number = create_response.json()["partner_number"]

    # Delete
    response = await client.delete(f"/api/partners/{partner_number}", headers=admin_headers)
    assert response.status_code == 204

    # Verify deleted
    get_response = await client.get(f"/api/partners/{partner_number}", headers=admin_headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_list_partners(client: AsyncClient, admin_headers):
    """Test listování partnerů"""
    # Create multiple partners
    for i in range(5):
        data = {
            "company_name": f"Partner {i}",
            "is_customer": i % 2 == 0,
            "is_supplier": i % 2 == 1
        }
        await client.post("/api/partners/", json=data, headers=admin_headers)

    # List all
    response = await client.get("/api/partners/", headers=admin_headers)
    assert response.status_code == 200

    partners = response.json()
    assert len(partners) >= 5


@pytest.mark.asyncio
async def test_filter_customers(client: AsyncClient, admin_headers):
    """Test filtrování pouze zákazníků"""
    # Create customer
    customer_data = {
        "company_name": "Customer Only",
        "is_customer": True,
        "is_supplier": False
    }
    await client.post("/api/partners/", json=customer_data, headers=admin_headers)

    # Create supplier
    supplier_data = {
        "company_name": "Supplier Only",
        "is_customer": False,
        "is_supplier": True
    }
    await client.post("/api/partners/", json=supplier_data, headers=admin_headers)

    # Filter customers
    response = await client.get("/api/partners/?partner_type=customer", headers=admin_headers)
    assert response.status_code == 200

    partners = response.json()
    for partner in partners:
        assert partner["is_customer"] is True


@pytest.mark.asyncio
async def test_filter_suppliers(client: AsyncClient, admin_headers):
    """Test filtrování pouze dodavatelů"""
    response = await client.get("/api/partners/?partner_type=supplier", headers=admin_headers)
    assert response.status_code == 200

    partners = response.json()
    for partner in partners:
        assert partner["is_supplier"] is True


@pytest.mark.asyncio
async def test_search_partners(client: AsyncClient, admin_headers):
    """Test vyhledávání partnerů"""
    # Create partner with unique name
    data = {
        "company_name": "UNIQUE_SEARCH_TEST s.r.o.",
        "email": "unique@search.test"
    }
    await client.post("/api/partners/", json=data, headers=admin_headers)

    # Search by company name
    response = await client.get("/api/partners/search?search=UNIQUE_SEARCH", headers=admin_headers)
    assert response.status_code == 200

    result = response.json()
    assert result["total"] >= 1
    found = any(p["company_name"] == "UNIQUE_SEARCH_TEST s.r.o." for p in result["partners"])
    assert found


@pytest.mark.asyncio
async def test_search_by_email(client: AsyncClient, admin_headers):
    """Test vyhledávání podle emailu"""
    # Create
    data = {
        "company_name": "Email Search Test",
        "email": "searchme@example.com"
    }
    await client.post("/api/partners/", json=data, headers=admin_headers)

    # Search
    response = await client.get("/api/partners/search?search=searchme@", headers=admin_headers)
    assert response.status_code == 200

    result = response.json()
    found = any(p["email"] == "searchme@example.com" for p in result["partners"])
    assert found


# ============================================================================
# ICO/DIC VALIDATION TESTS
# ============================================================================

def test_valid_ico():
    """Test validního IČO (mod 11 checksum)"""
    # Valid ICO: 27082440 (checksum correct)
    # Calculation: 2*8 + 7*7 + 0*6 + 8*5 + 2*4 + 4*3 + 4*2 = 16+49+0+40+8+12+8 = 133
    # 133 % 11 = 1, so expected digit = 0
    partner = PartnerCreate(
        company_name="Test",
        ico="27082440"
    )
    assert partner.ico == "27082440"


def test_invalid_ico_length():
    """Test IČO s neplatnou délkou"""
    with pytest.raises(ValidationError) as exc_info:
        PartnerCreate(
            company_name="Test",
            ico="1234567"  # 7 digits instead of 8
        )
    assert "8 číslic" in str(exc_info.value)


def test_invalid_ico_checksum():
    """Test IČO s neplatným kontrolním součtem"""
    with pytest.raises(ValidationError) as exc_info:
        PartnerCreate(
            company_name="Test",
            ico="27082441"  # Wrong checksum (should be 0, not 1)
        )
    assert "kontrolní součet" in str(exc_info.value)


def test_valid_dic_8_digits():
    """Test validního DIČ (CZ + 8 digits)"""
    partner = PartnerCreate(
        company_name="Test",
        dic="CZ12345678"
    )
    assert partner.dic == "CZ12345678"


def test_valid_dic_9_digits():
    """Test validního DIČ (CZ + 9 digits)"""
    partner = PartnerCreate(
        company_name="Test",
        dic="CZ123456789"
    )
    assert partner.dic == "CZ123456789"


def test_valid_dic_10_digits():
    """Test validního DIČ (CZ + 10 digits)"""
    partner = PartnerCreate(
        company_name="Test",
        dic="CZ1234567890"
    )
    assert partner.dic == "CZ1234567890"


def test_invalid_dic_no_cz_prefix():
    """Test DIČ bez CZ prefixu"""
    with pytest.raises(ValidationError) as exc_info:
        PartnerCreate(
            company_name="Test",
            dic="12345678"  # Missing CZ prefix
        )
    assert "začínat 'CZ'" in str(exc_info.value)


def test_invalid_dic_too_short():
    """Test DIČ s příliš krátkým číslem"""
    with pytest.raises(ValidationError) as exc_info:
        PartnerCreate(
            company_name="Test",
            dic="CZ1234567"  # Only 7 digits
        )
    assert "8-10 číslic" in str(exc_info.value)


def test_invalid_dic_too_long():
    """Test DIČ s příliš dlouhým číslem"""
    with pytest.raises(ValidationError) as exc_info:
        PartnerCreate(
            company_name="Test",
            dic="CZ12345678901"  # 11 digits
        )
    assert "8-10 číslic" in str(exc_info.value)


def test_dic_case_insensitive():
    """Test DIČ s lowercase 'cz' (should be uppercased)"""
    partner = PartnerCreate(
        company_name="Test",
        dic="cz12345678"
    )
    assert partner.dic == "CZ12345678"


def test_optional_ico_dic():
    """Test že IČO a DIČ jsou optional"""
    partner = PartnerCreate(
        company_name="Test Without ICO/DIC"
    )
    assert partner.ico is None
    assert partner.dic is None


def test_country_uppercase():
    """Test že country code je automaticky uppercase"""
    partner = PartnerCreate(
        company_name="Test",
        country="sk"
    )
    assert partner.country == "SK"
