"""
Centralized asynchronous HTTP client for direct communication with Discord API v10.
Implements:
- Official `User-Agent: DiscordBot (url, version)` header required by Discord documentation
- Pre-emptive Bucket Rate Limiting compliant with official Discord API library guidelines (meew0):
  * Groups routes by `(HTTP Method, Normalized Route, Major Parameter: guild_id / channel_id / webhook_id)`
  * Dynamically maps routes to `X-RateLimit-Bucket` hashes returned by Discord
  * Pre-emptively locks the bucket when `X-RateLimit-Remaining == 0` for `X-RateLimit-Reset-After` seconds
    to **prevent generating HTTP 429 responses**
  * Global rate-limit lock (`_global_lock`) for `X-RateLimit-Global`
- Persistent connection pooling (`aiohttp.ClientSession`), automatic retries on 5xx errors, and multipart uploads.
"""

import asyncio
import json
import logging
import re
import time
import urllib.parse
from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import FormData

from brazbot.errors import (
    BadRequest,
    DiscordServerError,
    Forbidden,
    HTTPException,
    NotFound,
    RateLimited,
    Unauthorized,
)

logger = logging.getLogger(__name__)

API_VERSION = 10
BASE_URL = f"https://discord.com/api/v{API_VERSION}"
LIBRARY_URL = "https://github.com/BosonsHiggs/brazbot.py"
LIBRARY_VERSION = "2.0.0"
USER_AGENT = f"DiscordBot ({LIBRARY_URL}, {LIBRARY_VERSION})"

# Regular expressions to extract Discord major route parameters
_MAJOR_PARAM_RE = re.compile(r"^/(channels|guilds|webhooks)/([0-9]{15,22}|@me)")
_SNOWFLAKE_SUB_RE = re.compile(r"/[0-9]{15,22}")


def compute_route_key(method: str, endpoint: str) -> str:
    """
    Computes the normalized route key respecting Discord Major Parameters
    (`channel_id`, `guild_id`, `webhook_id`).
    Minor Snowflakes in the URL are replaced with `:id` so they share the same rate-limit bucket.
    """
    clean_ep = "/" + endpoint.split("?")[0].lstrip("/")
    match = _MAJOR_PARAM_RE.match(clean_ep)
    if match:
        resource, major_id = match.group(1), match.group(2)
        prefix = f"/{resource}/{major_id}"
        rest = _SNOWFLAKE_SUB_RE.sub("/:id", clean_ep[len(prefix) :])
        return f"{method.upper()}:{prefix}{rest}"
    normalized = _SNOWFLAKE_SUB_RE.sub("/:id", clean_ep)
    return f"{method.upper()}:{normalized}"


class RateLimitBucket:
    """
    Represents an individual Discord API v10 Rate Limit bucket.
    Ensures requests wait pre-emptively whenever `remaining == 0`.
    """

    def __init__(self, key: str):
        self.key = key
        self.lock = asyncio.Lock()
        self.limit: int = 1
        self.remaining: int = 1
        self.reset_at: float = 0.0  # Monotonic timestamp when the bucket resets
        self.reset_after: float = 0.0
        self.last_status: int = 200

    async def acquire_preemptive_wait(self) -> None:
        """If the bucket is exhausted (`remaining == 0`), sleeps until `reset_at` before sending the request."""
        if self.remaining <= 0:
            now = time.monotonic()
            wait_seconds = self.reset_at - now
            if wait_seconds > 0:
                logger.debug(
                    f"[Pre-emptive RateLimit] Bucket '{self.key}' exhausted (remaining=0). "
                    f"Waiting {wait_seconds:.3f}s before dispatching request."
                )
                await asyncio.sleep(wait_seconds)
            self.remaining = 1

    def update_from_headers(self, headers: Any, status: int) -> None:
        """Updates bucket state from `X-RateLimit-*` HTTP response headers."""
        self.last_status = status
        limit_hdr = headers.get("X-RateLimit-Limit")
        rem_hdr = headers.get("X-RateLimit-Remaining")
        reset_after_hdr = headers.get("X-RateLimit-Reset-After")

        if limit_hdr is not None:
            try:
                self.limit = int(limit_hdr)
            except ValueError:
                pass
        if rem_hdr is not None:
            try:
                self.remaining = int(rem_hdr)
            except ValueError:
                pass
        if reset_after_hdr is not None:
            try:
                self.reset_after = float(reset_after_hdr)
                self.reset_at = time.monotonic() + self.reset_after
            except ValueError:
                pass


class HTTPClient:
    """
    Production HTTP client for Discord API v10.
    Reuses `aiohttp.ClientSession` and enforces pre-emptive per-bucket and global rate limiting.
    """

    def __init__(self, token: str, base_url: str = BASE_URL, max_retries: int = 5):
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None
        self._global_lock = asyncio.Event()
        self._global_lock.set()
        self._buckets: Dict[str, RateLimitBucket] = {}
        self._route_to_bucket_hash: Dict[str, str] = {}

    @property
    def default_headers(self) -> Dict[str, str]:
        headers = {
            "User-Agent": USER_AGENT,
        }
        if self.token:
            headers["Authorization"] = f"Bot {self.token}"
        return headers

    def _get_bucket(self, route_key: str) -> RateLimitBucket:
        bucket_hash = self._route_to_bucket_hash.get(route_key)
        if bucket_hash:
            major_part = route_key.split(":", 2)[-1].split("/")[:3]
            major_scope = "/".join(major_part)
            full_bucket_id = f"{bucket_hash}:{major_scope}"
        else:
            full_bucket_id = route_key
        if full_bucket_id not in self._buckets:
            self._buckets[full_bucket_id] = RateLimitBucket(full_bucket_id)
        return self._buckets[full_bucket_id]

    async def get_session(self) -> aiohttp.ClientSession:
        """Gets or creates the persistent HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=60, connect=15)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        """Closes the underlying HTTP session cleanly."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def _normalize_files(self, files: List[Any]) -> List[Dict[str, Any]]:
        """Normalizes various file representations (dict, File, bytes, file path) for multipart upload."""
        normalized: List[Dict[str, Any]] = []
        for idx, f in enumerate(files):
            if isinstance(f, dict):
                if "data" in f:
                    normalized.append(
                        {
                            "filename": f.get("filename", f"file_{idx}.bin"),
                            "data": f["data"],
                            "content_type": f.get("content_type", "application/octet-stream"),
                            "description": f.get("description"),
                        }
                    )
                elif "file" in f:
                    fp = f["file"]
                    data = fp.read() if hasattr(fp, "read") else fp
                    if hasattr(fp, "close"):
                        fp.close()
                    filename = getattr(fp, "name", f"file_{idx}.bin").split("/")[-1]
                    normalized.append(
                        {
                            "filename": f.get("filename", filename),
                            "data": data,
                            "content_type": f.get("content_type", "application/octet-stream"),
                            "description": f.get("description"),
                        }
                    )
            elif hasattr(f, "to_file_dict"):
                normalized.append(f.to_file_dict())
            elif hasattr(f, "to_dict"):
                d = f.to_dict()
                fp = d.get("file")
                data = fp.read() if hasattr(fp, "read") else b""
                if hasattr(fp, "close"):
                    fp.close()
                filename = (
                    getattr(f, "filename", None)
                    or getattr(f, "file_path", f"file_{idx}.bin").split("/")[-1]
                )
                normalized.append(
                    {
                        "filename": filename,
                        "data": data,
                        "content_type": getattr(f, "content_type", "application/octet-stream"),
                        "description": getattr(f, "description", None),
                    }
                )
            elif isinstance(f, (bytes, bytearray)):
                normalized.append(
                    {
                        "filename": f"attachment_{idx}.bin",
                        "data": bytes(f),
                        "content_type": "application/octet-stream",
                    }
                )
            elif isinstance(f, str):
                with open(f, "rb") as fp:
                    normalized.append(
                        {
                            "filename": f.split("/")[-1],
                            "data": fp.read(),
                            "content_type": "application/octet-stream",
                        }
                    )
        return normalized

    async def request(
        self,
        method: str,
        endpoint: str,
        *,
        json_data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        files: Optional[List[Any]] = None,
        reason: Optional[str] = None,
        auth: bool = True,
        full_url: Optional[str] = None,
        raise_on_error: bool = True,
    ) -> Any:
        """
        Executes an HTTP request to Discord API v10 with pre-emptive and automatic rate limiting.
        """
        url = full_url or f"{self.base_url}/{endpoint.lstrip('/')}"
        route_key = compute_route_key(method, endpoint or url)
        bucket = self._get_bucket(route_key)

        headers = dict(self.default_headers)
        if not auth:
            headers.pop("Authorization", None)
        if reason:
            headers["X-Audit-Log-Reason"] = urllib.parse.quote(str(reason), safe=" ")

        clean_params = None
        if params:
            clean_params = {k: str(v) for k, v in params.items() if v is not None}

        normalized_files = self._normalize_files(files) if files else []

        async with bucket.lock:
            for attempt in range(self.max_retries):
                # 1. Wait for global rate limit lock if active
                await self._global_lock.wait()
                # 2. Pre-emptively wait if the local bucket has 0 remaining requests
                await bucket.acquire_preemptive_wait()

                session = await self.get_session()
                req_kwargs: Dict[str, Any] = {"headers": dict(headers), "params": clean_params}

                if normalized_files:
                    form = FormData()
                    payload = dict(json_data) if isinstance(json_data, dict) else {}
                    attachments_meta = []
                    for i, nf in enumerate(normalized_files):
                        att_meta: Dict[str, Any] = {"id": i, "filename": nf["filename"]}
                        if nf.get("description"):
                            att_meta["description"] = nf["description"]
                        attachments_meta.append(att_meta)
                    if "data" in payload and isinstance(payload["data"], dict):
                        payload["data"]["attachments"] = attachments_meta
                    else:
                        payload["attachments"] = attachments_meta

                    form.add_field(
                        "payload_json",
                        json.dumps(payload),
                        content_type="application/json",
                    )
                    for i, nf in enumerate(normalized_files):
                        form.add_field(
                            f"files[{i}]",
                            nf["data"],
                            filename=nf["filename"],
                            content_type=nf["content_type"],
                        )
                    req_kwargs["data"] = form
                elif json_data is not None:
                    req_kwargs["json"] = json_data

                try:
                    async with session.request(method.upper(), url, **req_kwargs) as response:
                        resp_bucket = response.headers.get("X-RateLimit-Bucket")
                        if resp_bucket:
                            self._route_to_bucket_hash[route_key] = resp_bucket

                        bucket.update_from_headers(response.headers, response.status)

                        if response.status == 429:
                            body = await self._safe_parse(response)
                            retry_after = float(
                                (body.get("retry_after") if isinstance(body, dict) else None)
                                or response.headers.get("Retry-After", 1.0)
                            )
                            is_global = bool(
                                (body.get("global") if isinstance(body, dict) else False)
                                or response.headers.get("X-RateLimit-Global", "").lower() == "true"
                            )
                            scope = response.headers.get("X-RateLimit-Scope", "shared")
                            bucket.remaining = 0
                            bucket.reset_at = time.monotonic() + retry_after
                            logger.warning(
                                f"Rate limit 429 on {method} {endpoint} (scope={scope}, global={is_global}). "
                                f"Waiting {retry_after:.2f}s (attempt {attempt + 1}/{self.max_retries})"
                            )
                            if is_global:
                                self._global_lock.clear()
                                try:
                                    await asyncio.sleep(retry_after)
                                finally:
                                    self._global_lock.set()
                            else:
                                await asyncio.sleep(retry_after)
                            continue

                        if response.status in (500, 502, 503, 504) and attempt < self.max_retries - 1:
                            backoff = 1.0 + attempt * 1.5
                            logger.warning(
                                f"Discord server error {response.status} on {method} {endpoint}. "
                                f"Retrying in {backoff:.1f}s..."
                            )
                            await asyncio.sleep(backoff)
                            continue

                        if 200 <= response.status < 300:
                            if response.status == 204:
                                return True
                            return await self._safe_parse(response)

                        err_data = await self._safe_parse(response)
                        err_msg = (
                            err_data.get("message", str(err_data))
                            if isinstance(err_data, dict)
                            else str(err_data)
                        )
                        err_code = err_data.get("code") if isinstance(err_data, dict) else None
                        err_details = err_data.get("errors") if isinstance(err_data, dict) else None

                        if not raise_on_error:
                            logger.error(f"HTTP {response.status} on {method} {endpoint}: {err_msg}")
                            return None

                        if response.status == 400:
                            raise BadRequest(400, err_msg, err_code, err_details, err_data)
                        elif response.status == 401:
                            raise Unauthorized(401, err_msg, err_code, err_details, err_data)
                        elif response.status == 403:
                            raise Forbidden(403, err_msg, err_code, err_details, err_data)
                        elif response.status == 404:
                            raise NotFound(404, err_msg, err_code, err_details, err_data)
                        elif response.status >= 500:
                            raise DiscordServerError(
                                response.status, err_msg, err_code, err_details, err_data
                            )
                        else:
                            raise HTTPException(
                                response.status, err_msg, err_code, err_details, err_data
                            )

                except aiohttp.ClientError as e:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(1.0 + attempt)
                        continue
                    if not raise_on_error:
                        logger.error(f"Network error on {method} {endpoint}: {e}")
                        return None
                    raise HTTPException(0, f"Network error: {e}") from e

        if not raise_on_error:
            return None
        raise RateLimited(1.0)

    def get_rate_limit_snapshot(self) -> List[Dict[str, Any]]:
        """Returns the current state of all tracked rate-limit buckets without making extra HTTP calls."""
        now = time.monotonic()
        snapshot: List[Dict[str, Any]] = []
        for b in self._buckets.values():
            snapshot.append(
                {
                    "endpoint": b.key,
                    "status": b.last_status,
                    "limit": b.limit,
                    "remaining": b.remaining,
                    "reset": round(max(0.0, b.reset_at - now), 2),
                    "reset_after": round(b.reset_after, 2),
                    "bucket": b.key,
                    "retry_after": round(max(0.0, b.reset_at - now), 2) if b.remaining == 0 else 0,
                    "global": not self._global_lock.is_set(),
                }
            )
        return snapshot

    @staticmethod
    async def _safe_parse(response: aiohttp.ClientResponse) -> Any:
        text = await response.text()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
