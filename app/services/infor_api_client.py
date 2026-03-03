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
        # ℹ️ READONLY LIVE: Čtení z live Inforu povoleno.
        # Zápisy (POST transakce) jsou blokované v workshop_router.py.

        self.base_url = base_url.rstrip("/")
        self.config = config
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl

        # Token cache
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

        # Shared HTTP client (connection pool, reuse TCP/TLS)
        self._client: Optional[httpx.AsyncClient] = None

    def _get_http_client(self) -> httpx.AsyncClient:
        """Vrátí sdílený httpx client (connection pool, reuse TCP/TLS)."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                verify=self.verify_ssl,
                timeout=60.0,
                limits=httpx.Limits(max_connections=4, max_keepalive_connections=4),
            )
        return self._client

    async def close(self) -> None:
        """Uzavře sdílený HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

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

        client = self._get_http_client()
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
        properties: Optional[List[str]] = None,
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
            properties: Seznam polí ["Item", "Description", "UnitCost"].
                Pokud je None, endpoint se volá bez `props` a použije default view property set.
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
        props = ",".join(properties) if properties is not None else None

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
        if props is not None:
            params["props"] = props  # Add props as query parameter

        # Logujeme jen IDO a klíčové parametry, nikdy celý filter/URL (může být obrovský IN clause)
        log_params = {k: (v[:80] + "..." if isinstance(v, str) and len(v) > 80 else v) for k, v in params.items()}
        logger.info("LoadCollection: %s params=%s", ido_name, log_params)

        client = self._get_http_client()
        try:
            response = await client.get(
                url,
                params=params,
                headers={"Authorization": token},  # Infor: NO Bearer prefix
            )

            logger.info("Response: %s %d", ido_name, response.status_code)

            response.raise_for_status()

            data = response.json()

            result_array = None
            response_bookmark = None
            response_message = ""
            response_message_code = 0

            if isinstance(data, dict):
                response_bookmark = data.get("Bookmark") or data.get("bookmark")
                response_message = str(data.get("Message") or "")
                try:
                    response_message_code = int(data.get("MessageCode", 0) or 0)
                except (TypeError, ValueError):
                    response_message_code = 0

                result_array = data.get("Items")
                if result_array is None:
                    result_array = data.get("value", [])

            elif isinstance(data, list):
                result_array = data

            if result_array is None:
                return {
                    "data": [],
                    "bookmark": None,
                    "has_more": False,
                    "message": response_message,
                    "message_code": response_message_code,
                }

            field_names = properties or []
            result = []
            for row in result_array:
                if isinstance(row, list):
                    if row and isinstance(row[0], dict) and 'Name' in row[0] and 'Value' in row[0]:
                        obj = {}
                        for item in row:
                            if isinstance(item, dict) and 'Name' in item and 'Value' in item:
                                obj[item['Name']] = item['Value']
                        result.append(obj)
                    else:
                        obj = dict(zip(field_names, row))
                        result.append(obj)
                elif isinstance(row, dict):
                    result.append(row)

            logger.info(f"LoadCollection {ido_name}: {len(result)} rows")

            # Infor API stránkuje interně (typicky 200 řádků/stránku).
            # Bookmark existuje → jsou další stránky (nezáleží na record_cap).
            has_more = bool(response_bookmark) and len(result) > 0

            return {
                "data": result,
                "bookmark": response_bookmark,
                "has_more": has_more,
                "message": response_message,
                "message_code": response_message_code,
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

        client = self._get_http_client()
        try:
            response = await client.get(
                f"{self.base_url}/json/idoinfo/{ido_name}",
                headers={"Authorization": token},
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

        client = self._get_http_client()
        try:
            response = await client.get(
                f"{self.base_url}/json/method/{ido_name}/{method_name}",
                params=params,
                headers={"Authorization": token},
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

    async def post_method(
        self,
        ido_name: str,
        method_name: str,
        parameters: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Volání IDO business metody přes HTTP POST (pro stored procedure writes).

        Použij místo invoke_method() pokud metoda mutuje data v Inforu
        (např. IteCzTsdUpdateDcJmcSp).

        Args:
            ido_name: Název IDO (např. "IteCzTsdStd")
            method_name: Název metody (např. "IteCzTsdUpdateDcJmcSp")
            parameters: Parametry metody jako slovník

        Returns:
            Dict s výsledkem metody
        """
        token = await self.get_token()
        body = {"Parameters": parameters or {}}

        logger.debug(f"POST InvokeMethod: {ido_name}.{method_name}({parameters})")

        client = self._get_http_client()
        try:
            response = await client.post(
                f"{self.base_url}/json/method/{ido_name}/{method_name}",
                json=body,
                headers={
                    "Authorization": token,
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"POST InvokeMethod failed: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"POST InvokeMethod error: {e}")
            raise

    async def invoke_method_params(
        self,
        ido_name: str,
        method_name: str,
        params: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Volání IDO metody přes POST s pojmenovanými parametry a IsOutput flagy.

        Formát identický s InduStream (Fiddler HAR):
          POST /json/method/{ido}/{method}
          Body: {"Params": [{"ParamName": "P0", "Value": "...", "IsOutput": true}, ...]}

        Args:
            ido_name: Název IDO (např. "IteCzTsdStd")
            method_name: Název metody
            params: List of param dicts: [{"ParamName": "P0", "Value": "x", "IsOutput": True}, ...]

        Returns:
            Dict s výsledkem {"Message": ..., "MessageCode": ..., "Params": [...]}
        """
        token = await self.get_token()

        body = {"Params": params}

        logger.info(
            "InvokeMethod POST: %s.%s param_count=%d",
            ido_name, method_name, len(params),
        )
        logger.debug("InvokeMethod POST body: %s", body)

        client = self._get_http_client()
        try:
            # Trailing slash required — Infor IIS returns 307 redirect without it
            response = await client.post(
                f"{self.base_url}/json/method/{ido_name}/{method_name}/",
                json=body,
                headers={
                    "Authorization": token,
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            logger.debug("InvokeMethod POST response: %s", result)

            # Normalize response: map "Params" → "Parameters" for compatibility
            if "Params" in result and "Parameters" not in result:
                # Extract values from Params array into Parameters list
                out_params = []
                for p in result.get("Params", []):
                    out_params.append(p.get("Value"))
                result["Parameters"] = out_params

            return result
        except httpx.HTTPStatusError as e:
            logger.error(
                "InvokeMethod POST failed: %s - %s",
                e.response.status_code, e.response.text[:500],
            )
            raise
        except Exception as e:
            logger.error("InvokeMethod POST error: %s", e)
            raise

    async def invoke_method_positional(
        self,
        ido_name: str,
        method_name: str,
        positional_values: List[str],
    ) -> Dict[str, Any]:
        """
        Volání IDO metody přes GET s pozičními parametry v ?parms=v1,v2,...

        Infor REST API požaduje parametry jako JEDEN parms query param s hodnotami
        oddělenými čárkou (pozičně odpovídají @parametrům SP v jejich pořadí).

        IMPORTANT: Commas in parms are literal delimiters (NOT URL-encoded).
        Only individual parameter values are URL-encoded.
        Zjištěno z WSDL: UriTemplate = /json/method/{ido}/{method}?parms={parms}

        Args:
            ido_name: Název IDO (např. "IteCzTsdStd")
            method_name: Název metody (např. "IteCzTsdUpdateDcSfc34Sp")
            positional_values: Hodnoty parametrů v pořadí jak SP je očekává

        Returns:
            Dict s výsledkem {"Message": ..., "MessageCode": ..., "ReturnValue": ...}
        """
        token = await self.get_token()

        # URL-encode individual values but keep commas as literal delimiters.
        # Infor REST API UriTemplate expects: ?parms=v1,v2,v3,...
        # Commas are structural delimiters, NOT part of values.
        from urllib.parse import quote
        encoded_values = [quote(str(v), safe="") for v in positional_values]
        parms = ",".join(encoded_values)

        logger.info(
            "InvokeMethod positional: %s.%s param_count=%d",
            ido_name, method_name, len(positional_values),
        )
        logger.debug("InvokeMethod positional parms: %s", parms[:300])

        # Build URL manually — do NOT let httpx encode the query string,
        # because it would encode commas as %2C which breaks Infor parsing.
        url = f"{self.base_url}/json/method/{ido_name}/{method_name}?parms={parms}"

        client = self._get_http_client()
        try:
            response = await client.get(
                url,
                headers={"Authorization": token},
                timeout=30.0
            )
            logger.info("InvokeMethod positional response URL: %s", response.url)
            response.raise_for_status()
            result = response.json()
            logger.debug("InvokeMethod positional response body: %s", result)
            return result
        except httpx.HTTPStatusError as e:
            logger.error(
                "InvokeMethod positional failed: %s - %s",
                e.response.status_code, e.response.text,
            )
            raise
        except Exception as e:
            logger.error("InvokeMethod positional error: %s", e)
            raise

    async def additem(
        self,
        ido_name: str,
        properties: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Vloží nový záznam do IDO přes AddItem endpoint.

        Ověřeno na SLJobTrans: POST /json/{ido}/additem s
        {"Properties": [{"Name": k, "Value": v}...]}

        Args:
            ido_name: Název IDO (např. "SLJobTrans")
            properties: Dict s hodnotami polí pro nový záznam

        Returns:
            Dict s výsledkem {"Message": ..., "MessageCode": ..., "UpdatedItems": ...}

        Raises:
            Exception při selhání (MessageCode != 200)
        """
        token = await self.get_token()
        body = {
            "Properties": [
                {"Name": k, "Value": v}
                for k, v in properties.items()
            ]
        }

        logger.debug(f"AddItem: {ido_name} with {list(properties.keys())}")

        client = self._get_http_client()
        try:
            response = await client.post(
                f"{self.base_url}/json/{ido_name}/additem",
                json=body,
                headers={
                    "Authorization": token,
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            if data.get("MessageCode") not in (0, 200):
                msg = data.get("Message", "Unknown error")
                logger.error(f"AddItem {ido_name} failed: [{data.get('MessageCode')}] {msg}")
                raise ValueError(f"Infor AddItem failed: {msg}")

            logger.info(f"AddItem {ido_name} succeeded")
            return data
        except httpx.HTTPStatusError as e:
            logger.error(f"AddItem HTTP failed: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"AddItem error: {e}")
            raise

    async def execute_update_request(
        self,
        request_body: Dict[str, Any],
        response_mode: str = "summary",
    ) -> Dict[str, Any]:
        """
        Spustí UpdateCollection request přes /json/updaterequest.

        Poznámka:
        - Na některých instalacích (IIS verb filtering) nemusí fungovat PUT /updateitem.
          Tento endpoint je stabilní fallback pro update existujících záznamů.
        - request_body má tvar UpdateCollectionRequest (IDOName, Changes, ...).
        """
        token = await self.get_token()

        client = self._get_http_client()
        try:
            response = await client.post(
                f"{self.base_url}/json/updaterequest",
                params={"response": response_mode},
                json=request_body,
                headers={
                    "Authorization": token,
                    "Content-Type": "application/json",
                    "accept": "application/json",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "ExecuteUpdateRequest failed: %s - %s",
                e.response.status_code,
                e.response.text,
            )
            raise
        except Exception as e:
            logger.error(f"ExecuteUpdateRequest error: {e}")
            raise

    async def get_configurations(self) -> List[str]:
        """
        Získat seznam dostupných konfigurací.

        Returns:
            List of configuration names (např. ["SL", "PROD", "TEST"])
        """
        logger.debug("Getting available configurations")

        client = self._get_http_client()
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
