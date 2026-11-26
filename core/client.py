"""Cliente HTTP con reintentos, tiempo límite y registro de errores en el diagnóstico."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .diagnostics import Diagnostics


@dataclass
class FetchResult:
    url: str
    status: Optional[int] = None
    content_type: str = ""
    content: bytes = b""
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.status == 200

    def json(self):
        import json
        return json.loads(self.content.decode("utf-8"))


class HttpClient:
    def __init__(self, settings, diag: Diagnostics | None = None):
        self.s = settings
        self.diag = diag or Diagnostics()
        self.session = requests.Session()
        retry = Retry(total=settings.retries, backoff_factor=1.0,
                      status_forcelist=[429, 500, 502, 503, 504],
                      allowed_methods=["GET"], raise_on_status=False)
        self.session.mount("http://", HTTPAdapter(max_retries=retry))
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.headers["User-Agent"] = settings.user_agent

    def get(self, url: str, params: dict | None = None) -> FetchResult:
        try:
            r = self.session.get(url, params=params, timeout=self.s.request_timeout)
        except requests.RequestException as e:
            self.diag.http_error(f"red:{type(e).__name__}")
            return FetchResult(url=url, error=f"{type(e).__name__}: {e}")
        res = FetchResult(url=r.url, status=r.status_code,
                          content_type=r.headers.get("Content-Type", ""), content=r.content)
        if r.status_code != 200:
            self.diag.http_error(r.status_code)
        return res
