"""Mongoose / Infor Process Server (IPS) session client.

Implements the stateful binary-framed session protocol used by InduStream
to communicate with Infor SyteLine.  This is NOT the REST IDO API — it's
the proprietary IPS protocol that maintains server-side session state
between SP calls (critical for TSD init context → WrapperSp flow).

Protocol (from HAR trace analysis):
  POST /session/create   → JSON → get token
  POST /session/login    → Authorization: <token> + JSON creds → authenticated
  PUT  /session/data     → Authorization: <token> + binary frame (50B hdr + JSON)
  GET  /session/keepalive → keep session alive (TTL ~5 min)

Binary frame format (50 bytes header):
  [0:2]   uint16 LE  marker (request: 0x00FE?, response: 0x00FF)
  [2:4]   uint16 LE  command_type (0x0022 = InvokeMethod)
  [4:8]   uint32 LE  payload_length (JSON bytes after header)
  [8:24]  16 bytes   request GUID (correlation ID, echoed in response)
  [24:50] 26 bytes   reserved (zeros)
"""

import asyncio
import hashlib
import base64
import struct
import uuid
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# Command types observed in HAR
CMD_OPEN_MODULE = 0x003D
CMD_LOAD_COLLECTION = 0x0020
CMD_METHOD_COLLECTION = 0x0021
CMD_INVOKE_METHOD = 0x0022


class MongooseSessionError(Exception):
    """Error from Mongoose session operations."""
    pass


class MongooseSession:
    """Stateful session client for Infor Process Server (Mongoose/IPS).

    Usage:
        session = MongooseSession("http://192.168.1.17:8501")
        await session.connect(user="tsd", password="secret", config="Live")
        result = await session.invoke_method("IteCzTsdStd", "SomeSp", [...])
        await session.close()

    Or as async context manager:
        async with MongooseSession("http://192.168.1.17:8501") as session:
            await session.connect(user="tsd", password="secret", config="Live")
            result = await session.invoke_method(...)
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        keepalive_interval: float = 120.0,  # seconds between keepalives
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.keepalive_interval = keepalive_interval
        self.token: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._keepalive_task: Optional[asyncio.Task] = None
        self._connected = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()

    @property
    def connected(self) -> bool:
        return self._connected and self.token is not None

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    async def connect(
        self,
        user: str,
        password: str,
        config: str = "Live",
        pwd_is_hash: bool = False,
        hostname: str = "GESTIMA",
    ) -> None:
        """Create session, login, and start keepalive.

        Args:
            user: Infor username (e.g. "tsd")
            password: Plain-text password OR base64 SHA-256 hash
            config: Infor configuration name (e.g. "Live")
            pwd_is_hash: If True, password is already base64(SHA-256(pwd))
            hostname: Client hostname identifier
        """
        self._client = httpx.AsyncClient(timeout=self.timeout, verify=False)

        # Step 1: Create session
        self.token = await self._create_session(hostname)
        logger.info("MONGOOSE session created: token=%s...", self.token[:20])

        # Step 2: Login
        pwd_hash = password if pwd_is_hash else self._hash_password(password)
        await self._login(user, pwd_hash, config)
        logger.info("MONGOOSE session logged in: user=%s config=%s", user, config)

        # Step 3: Open module (required before SP calls)
        await self._open_module()

        self._connected = True

        # Step 4: Start keepalive background task
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())

    async def close(self) -> None:
        """Close session and stop keepalive."""
        self._connected = False
        if self._keepalive_task and not self._keepalive_task.done():
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass
        if self._client:
            await self._client.aclose()
            self._client = None
        self.token = None
        logger.info("MONGOOSE session closed")

    async def reconnect(
        self,
        user: str,
        password: str,
        config: str = "Live",
        pwd_is_hash: bool = False,
        hostname: str = "GESTIMA",
    ) -> None:
        """Close and re-establish session."""
        await self.close()
        await self.connect(user, password, config, pwd_is_hash, hostname)

    # ------------------------------------------------------------------
    # Public API: invoke_method
    # ------------------------------------------------------------------

    async def invoke_method(
        self,
        ido_name: str,
        method_name: str,
        params: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Call an IDO stored procedure within the session.

        Args:
            ido_name: IDO name (e.g. "IteCzTsdStd")
            method_name: SP name (e.g. "IteCzTsdUpdateDcSfcWrapperSp")
            params: List of {"ParamName": "P0", "Value": "...", "IsOutput": True}

        Returns:
            Response dict with "Params" and "Severity" keys.

        Raises:
            MongooseSessionError on communication or protocol errors.
        """
        if not self.connected:
            raise MongooseSessionError("Session not connected")

        payload = {
            "IDOName": ido_name,
            "MethodName": method_name,
            "Params": params,
        }

        resp_json = await self._send_data(CMD_INVOKE_METHOD, payload)

        severity = str(resp_json.get("Severity", "0"))
        if severity not in ("0",):
            logger.warning(
                "MONGOOSE %s.%s Severity=%s: %s",
                ido_name, method_name, severity, resp_json,
            )

        # Normalize: map "Params" to flat "Parameters" list for compatibility
        params_arr = resp_json.get("Params", [])
        flat_params = []
        for p in params_arr:
            flat_params.append(p.get("Value", "") or "")
        resp_json["Parameters"] = flat_params

        return resp_json

    async def load_collection(
        self,
        ido_name: str,
        output_columns: List[str],
        method_name: Optional[str] = None,
        params: Optional[List[Dict[str, Any]]] = None,
        filter_str: Optional[str] = None,
        order_by: Optional[str] = None,
        row_count: int = 0,
    ) -> Dict[str, Any]:
        """Load collection (IDO query) within the session.

        For simple queries (no method), uses CMD_LOAD_COLLECTION.
        For method-backed queries, uses CMD_METHOD_COLLECTION.
        """
        if not self.connected:
            raise MongooseSessionError("Session not connected")

        if method_name:
            payload = {
                "AppendTypes": True,
                "IDOName": ido_name,
                "MethodName": method_name,
                "OutputColumns": output_columns,
                "Params": params or [],
                "RowCount": row_count,
            }
            return await self._send_data(CMD_METHOD_COLLECTION, payload)
        else:
            payload = {
                "AppendTypes": True,
                "Distinct": False,
                "Filter": filter_str or "",
                "IDOName": ido_name,
                "OrderBy": order_by,
                "OutputColumns": output_columns,
                "RowCount": row_count,
            }
            return await self._send_data(CMD_LOAD_COLLECTION, payload)

    # ------------------------------------------------------------------
    # Internal: session management
    # ------------------------------------------------------------------

    async def _create_session(self, hostname: str) -> str:
        """POST /session/create → get session token."""
        body = {
            "wsid": str(uuid.uuid4()),
            "ccid": str(uuid.uuid4()),
            "apptype": "INS",
            "platform": "Gestima TSD Client",
            "hostname": hostname,
            "versioninstaller": "8.0.2.11126",
            "versionfiles": "Core,8.5.2.8031;Launcher,8.1.0.11023;Forms_Std,8.5.2.42;Forms_Cust,7.0.0.0;Forms_CustExt,7.0.0.0;ExtTools,0.0.0.0",
            "noupdate": True,
        }
        resp = await self._client.post(
            f"{self.base_url}/session/create",
            json=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        resp.raise_for_status()
        data = resp.json()
        token = data.get("token")
        if not token:
            raise MongooseSessionError(f"No token in create response: {data}")
        return token

    async def _login(self, user: str, pwd_hash: str, config: str) -> Dict[str, Any]:
        """POST /session/login → authenticate."""
        body = {
            "config": config,
            "langid": -1,
            "pwd": pwd_hash,
            "reccount": -1,
            "token": self.token,
            "user": user,
        }
        resp = await self._client.post(
            f"{self.base_url}/session/login",
            json=body,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": self.token,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if "token" not in data:
            raise MongooseSessionError(f"Login failed: {data}")
        return data

    async def _open_module(self) -> None:
        """Send OpenModule command (required before SP calls)."""
        payload = {"IdModule": 0, "IdModuleLast": -1, "IsOpen": True}
        await self._send_data(CMD_OPEN_MODULE, payload)
        logger.debug("MONGOOSE OpenModule sent")

    async def _keepalive_loop(self) -> None:
        """Background keepalive task."""
        while self._connected:
            try:
                await asyncio.sleep(self.keepalive_interval)
                if not self._connected:
                    break
                await self._client.get(
                    f"{self.base_url}/session/keepalive",
                    headers={"Authorization": self.token},
                )
                logger.debug("MONGOOSE keepalive OK")
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("MONGOOSE keepalive failed: %s", exc)

    # ------------------------------------------------------------------
    # Internal: binary frame protocol
    # ------------------------------------------------------------------

    def _build_frame(self, command_type: int, json_payload: bytes) -> bytes:
        """Build 50-byte header + JSON payload.

        Header layout (little-endian):
          [0:2]   uint16  marker (0x00FE for request)
          [2:4]   uint16  command_type
          [4:8]   uint32  payload_length
          [8:24]  16 bytes  request GUID
          [24:50] 26 bytes  zeros (reserved)
        """
        request_guid = uuid.uuid4().bytes  # 16 bytes
        payload_len = len(json_payload)

        header = struct.pack("<HHI", 0x00FE, command_type, payload_len)
        header += request_guid
        header += b"\x00" * 26  # reserved

        assert len(header) == 50, f"Header must be 50 bytes, got {len(header)}"
        return header + json_payload

    def _parse_frame(self, raw: bytes) -> Dict[str, Any]:
        """Parse 50-byte header + JSON payload from response.

        Returns parsed JSON dict. Returns empty dict if no payload.
        """
        if len(raw) < 50:
            raise MongooseSessionError(
                f"Response too short: {len(raw)} bytes (need ≥50)"
            )

        marker, cmd_type, payload_len = struct.unpack("<HHI", raw[:8])
        # request_guid = raw[8:24]  # for correlation if needed

        if payload_len == 0:
            return {}

        json_bytes = raw[50:50 + payload_len]
        if len(json_bytes) < payload_len:
            raise MongooseSessionError(
                f"Truncated payload: got {len(json_bytes)}, expected {payload_len}"
            )

        import json
        try:
            return json.loads(json_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise MongooseSessionError(f"Failed to parse response JSON: {exc}")

    async def _send_data(self, command_type: int, payload: dict) -> Dict[str, Any]:
        """Send binary-framed request to /session/data, return parsed response."""
        import json
        json_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        frame = self._build_frame(command_type, json_bytes)

        logger.debug(
            "MONGOOSE send cmd=0x%04X payload=%d bytes",
            command_type, len(json_bytes),
        )

        resp = await self._client.put(
            f"{self.base_url}/session/data",
            content=frame,
            headers={
                "Authorization": self.token,
                "Content-Type": "application/octet-stream",
            },
        )
        resp.raise_for_status()

        result = self._parse_frame(resp.content)
        logger.debug("MONGOOSE recv cmd=0x%04X result_keys=%s", command_type, list(result.keys()) if result else "empty")
        return result

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _hash_password(plain_password: str) -> str:
        """Hash password as base64(SHA-256(password)) — matching InduStream format."""
        sha = hashlib.sha256(plain_password.encode("utf-8")).digest()
        return base64.b64encode(sha).decode("ascii")
