"""GESTIMA - Infor CloudSuite Industrial API Client"""

import httpx
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class InforAPIClient:
    """
    Client pro Infor CloudSuite Industrial REST API (JSON format).

    Podporuje:
    - Token-based authentication
    - LoadCollection (čtení dat z IDO)
    - GetIDOInfo (discovery - jaké fields IDO má)
    - InvokeMethod (volání business logiky)

    Příklad použití:
        client = InforAPIClient(
            base_url="https://util90110.kovorybka.cz",
            config="SL",
            username="user",
            password="pass"
        )

        # Načíst položky
        items = await client.load_collection(
            ido_name="SLItems",
            properties=["Item", "Description", "UnitCost"],
            filter="Item LIKE 'A%'",
            record_cap=100
        )
    """

    def __init__(
        self,
        base_url: str,
        config: str = "TEST",
        username: str = "",
        password: str = "",
        verify_ssl: bool = False  # Default False pro self-signed certs
    ):
        # 🚨 SECURITY: NEVER allow LIVE config!
        if config.upper() in ["LIVE", "PROD", "PRODUCTION", "SL"]:
            raise ValueError(
                "CRITICAL SECURITY ERROR: Using production config is FORBIDDEN! "
                f"Config '{config}' is not allowed. Use 'Test' or 'Demo' config only. "
                "This prevents accidental corruption of production data."
            )

        self.base_url = base_url.rstrip("/")
        self.config = config
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl

        # Token cache
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

    async def get_token(self) -> str:
        """
        Získat nebo obnovit security token.
        Token je cached a automaticky obnovován před expirací.
        """
        # Pokud máme platný token, vrátit ho
        if self._token and self._token_expires and self._token_expires > datetime.now():
            return self._token

        # Jinak získat nový token
        logger.info(f"Requesting new token from Infor API (config={self.config})")

        async with httpx.AsyncClient(verify=self.verify_ssl) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/json/token/{self.config}",
                    headers={
                        "UserId": self.username,
                        "Password": self.password,
                        "accept": "application/json"
                    },
                    timeout=30.0
                )
                response.raise_for_status()

                data = response.json()

                # Response může být různý formát - zkusit všechny varianty
                self._token = (
                    data.get("Token") or  # Infor format (capital T)
                    data.get("token") or
                    data.get("SecurityToken") or
                    data.get("value")
                )

                if not self._token:
                    raise ValueError(f"Token not found in response: {data}")

                # Token platný 60 minut (SyteLine default), obnovit po 55 min
                self._token_expires = datetime.now() + timedelta(minutes=55)

                logger.info(f"Token acquired successfully, expires at {self._token_expires}")
                return self._token

            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to get token: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Failed to get token: {e}")
                raise

    async def load_collection(
        self,
        ido_name: str,
        properties: List[str],
        filter: Optional[str] = None,
        order_by: Optional[str] = None,
        record_cap: int = 0,  # 0 = unlimited
        load_type: Optional[str] = None,  # FIRST | NEXT | PREVIOUS | LAST
        bookmark: Optional[str] = None,  # Bookmark ID for pagination
        distinct: bool = False  # SQL DISTINCT
    ) -> Dict[str, Any]:
        """
        Načíst data z IDO (Intelligent Data Object).

        Args:
            ido_name: Název IDO (např. "SLItems", "SLCustomers")
            properties: Seznam polí ["Item", "Description", "UnitCost"]
            filter: WHERE podmínka (např. "Item = 'ABC123'" nebo "Item LIKE 'A%'")
            order_by: Řazení (např. "Item ASC" nebo "UnitCost DESC")
            record_cap: Max počet záznamů (0 = unlimited, -1 = default)
            load_type: Type of load - FIRST | NEXT | PREVIOUS | LAST
            bookmark: Bookmark ID from previous response for pagination
            distinct: Use SQL DISTINCT

        Returns:
            Dict with:
                - data: List of dicts [{"Item": "ABC123", "Description": "..."}, ...]
                - bookmark: Bookmark ID for next page (if available)
                - has_more: Boolean indicating if more records exist
        """
        token = await self.get_token()
        props = ",".join(properties)

        # Build query parameters
        params: Dict[str, Any] = {}
        if filter:
            params["filter"] = filter
        if order_by:
            params["orderBy"] = order_by
        # rowcap: -1 = don't send (API default 200), 0 = unlimited, >0 = specific limit
        if record_cap >= 0:
            params["rowcap"] = record_cap
        # If record_cap == -1, don't send rowcap parameter at all (API uses default 200)
        if load_type:
            params["loadtype"] = load_type
        if bookmark:
            params["bookmark"] = bookmark
        if distinct:
            params["distinct"] = "true"

        # Use /adv endpoint for advanced queries with rowcap support
        url = f"{self.base_url}/json/{ido_name}/adv"
        params["props"] = props  # Add props as query parameter

        logger.info(f"LoadCollection: {ido_name} with params {params}")
        logger.info(f"Request URL: {url}")

        async with httpx.AsyncClient(verify=self.verify_ssl) as client:
            try:
                response = await client.get(
                    url,
                    params=params,
                    headers={"Authorization": token},  # Infor: NO Bearer prefix
                    timeout=60.0
                )

                # Log actual request URL for debugging
                logger.info(f"Actual request URL: {response.request.url}")

                logger.info(f"Response status: {response.status_code}")
                logger.info(f"Response headers: {dict(response.headers)}")

                response.raise_for_status()

                data = response.json()

                # DEBUG: Log raw response
                logger.info(f"Raw response type: {type(data)}")
                logger.info(f"Raw response (first 500 chars): {str(data)[:500]}")

                # Response format může být různý
                # Swagger-style endpoint returns dict with "Items" as array of arrays
                # Need to convert to array of objects: [{"Field": "value1"}, {"Field": "value2"}, ...]

                result_array = None
                response_bookmark = None

                if isinstance(data, dict):
                    logger.info(f"Response is dict with keys: {list(data.keys())}")

                    # Extract bookmark for pagination
                    response_bookmark = data.get("Bookmark") or data.get("bookmark")

                    # Extract Items array (Infor CloudSuite format)
                    result_array = data.get("Items")
                    if result_array is not None:
                        logger.info(f"Extracted {len(result_array)} records from 'Items' key")
                    else:
                        # Fallback to "value" (generic format)
                        result_array = data.get("value", [])
                        logger.info(f"Extracted {len(result_array)} records from 'value' key")

                elif isinstance(data, list):
                    logger.info(f"Response is list with {len(data)} records")
                    result_array = data

                if result_array is None:
                    logger.warning(f"Unexpected response format: {type(data)}")
                    return {"data": [], "bookmark": None, "has_more": False}

                # Convert array of arrays to array of objects
                # properties is a list like ["Item", "Description"]
                # result_array can be:
                # 1. [["ABC", "Desc1"], ["DEF", "Desc2"]]  (simple arrays)
                # 2. [[{"Name": "Item", "Value": "ABC"}, {"Name": "Description", "Value": "Desc1"}], ...]  (/adv format)
                field_names = properties
                result = []
                for row in result_array:
                    if isinstance(row, list):
                        # Check if it's /adv format (array of Name/Value objects)
                        if row and isinstance(row[0], dict) and 'Name' in row[0] and 'Value' in row[0]:
                            # /adv format: [{"Name": "Item", "Value": "ABC"}, {"Name": "Description", "Value": "Desc"}]
                            # Convert to: {"Item": "ABC", "Description": "Desc"}
                            obj = {}
                            for item in row:
                                if isinstance(item, dict) and 'Name' in item and 'Value' in item:
                                    obj[item['Name']] = item['Value']
                            result.append(obj)
                            logger.debug(f"/adv format detected, converted to: {obj}")
                        else:
                            # Simple array format: ["ABC", "Desc1"]
                            # Create object by zipping field names with values
                            obj = dict(zip(field_names, row))
                            result.append(obj)
                    elif isinstance(row, dict):
                        # Already an object, use as is
                        result.append(row)
                    else:
                        logger.warning(f"Unexpected row format: {type(row)}")

                logger.info(f"Converted {len(result)} records to objects")

                # Return data with pagination info
                # has_more: If there's a bookmark, there might be more data
                # Special case: if record_cap=0 (unlimited), we got 200 (hard limit), so check bookmark
                # Normal case: if we got exactly what we asked for, there might be more
                has_more = False
                if response_bookmark:
                    if record_cap == 0:
                        # Unlimited request but got data - if there's a bookmark, there's more
                        has_more = len(result) > 0
                    else:
                        # Limited request - if we got exactly the limit, there might be more
                        has_more = len(result) == record_cap

                return {
                    "data": result,
                    "bookmark": response_bookmark,
                    "has_more": has_more
                }

            except httpx.HTTPStatusError as e:
                logger.error(f"LoadCollection failed: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"LoadCollection error: {e}")
                raise

    async def get_ido_info(self, ido_name: str) -> Dict[str, Any]:
        """
        Získat metadata o IDO - jaké fields existují, jejich typy, atd.

        Užitečné pro discovery - zjistit, jaké properties má např. SLItems.

        Args:
            ido_name: Název IDO (např. "SLItems")

        Returns:
            Dict s informacemi o IDO properties
        """
        token = await self.get_token()

        logger.debug(f"Getting IDO info for: {ido_name}")

        async with httpx.AsyncClient(verify=self.verify_ssl) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/json/idoinfo/{ido_name}",
                    headers={"Authorization": token},  # Infor: NO Bearer prefix
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"GetIDOInfo failed: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"GetIDOInfo error: {e}")
                raise

    async def invoke_method(
        self,
        ido_name: str,
        method_name: str,
        parameters: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Volání IDO business metody.

        Příklad:
            result = await client.invoke_method(
                "SLItems",
                "GetItemCost",
                {"Item": "ABC123", "Date": "2026-02-02"}
            )

        Args:
            ido_name: Název IDO
            method_name: Název metody
            parameters: Parametry metody

        Returns:
            Dict s výsledkem metody
        """
        token = await self.get_token()
        params = parameters or {}

        logger.debug(f"Invoking method: {ido_name}.{method_name}({params})")

        async with httpx.AsyncClient(verify=self.verify_ssl) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/json/method/{ido_name}/{method_name}",
                    params=params,
                    headers={"Authorization": token},  # Infor: NO Bearer prefix
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"InvokeMethod failed: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"InvokeMethod error: {e}")
                raise

    async def get_configurations(self) -> List[str]:
        """
        Získat seznam dostupných konfigurací.

        Returns:
            List of configuration names (např. ["SL", "PROD", "TEST"])
        """
        logger.debug("Getting available configurations")

        async with httpx.AsyncClient(verify=self.verify_ssl) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/json/configurations",
                    headers={
                        "UserId": self.username,
                        "Password": self.password,
                        "accept": "application/json"
                    },
                    timeout=30.0
                )
                response.raise_for_status()

                data = response.json()

                # Response může být list nebo dict
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return data.get("value", [])
                else:
                    return []

            except httpx.HTTPStatusError as e:
                logger.error(f"GetConfigurations failed: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"GetConfigurations error: {e}")
                raise

    async def discover_ido_names(self, common_names: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        Discovery tool - zjistit, které běžné IDO názvy existují.

        Zkusí načíst IDOInfo pro běžné názvy a vrátí, které fungují.

        Args:
            common_names: List IDO názvů k vyzkoušení (pokud None, použije default list)

        Returns:
            Dict[ido_name, exists]: {"SLItems": True, "Items": False, ...}
        """
        if common_names is None:
            # Default list běžných IDO názvů pro materiály/položky
            common_names = [
                "SLItems",
                "Items",
                "ItemMaster",
                "Item",
                "SLCustomers",
                "Customers",
                "SLCoOrders",
                "CoOrders",
                "SLVendors",
                "Vendors"
            ]

        logger.info(f"Discovering IDO names: {common_names}")

        results = {}

        for ido_name in common_names:
            try:
                await self.get_ido_info(ido_name)
                results[ido_name] = True
                logger.info(f"✓ IDO found: {ido_name}")
            except Exception:
                results[ido_name] = False
                logger.debug(f"✗ IDO not found: {ido_name}")

        return results
