"""Serve a FastMCP server over HTTPS using mkcert-generated local certs.

Claude Desktop's custom connectors require an https:// URL -- FastMCP's own
mcp.run(transport="streamable-http") has no SSL option, so this runs the
same Starlette ASGI app (mcp.streamable_http_app()) through uvicorn directly,
mirroring FastMCP's internal run_streamable_http_async(), with cert/key added.

Regenerate certs with: mkcert -install && cd certs && mkcert localhost 127.0.0.1
"""
from pathlib import Path

import uvicorn

CERT_DIR = Path(__file__).parent / "certs"
CERTFILE = CERT_DIR / "localhost+1.pem"
KEYFILE = CERT_DIR / "localhost+1-key.pem"


def serve_https(mcp) -> None:
    if not CERTFILE.exists() or not KEYFILE.exists():
        raise FileNotFoundError(
            f"Missing cert files in {CERT_DIR}. Generate with:\n"
            f"  mkcert -install && cd certs && mkcert localhost 127.0.0.1"
        )
    app = mcp.streamable_http_app()
    uvicorn.run(
        app,
        host=mcp.settings.host,
        port=mcp.settings.port,
        log_level=mcp.settings.log_level.lower(),
        ssl_keyfile=str(KEYFILE),
        ssl_certfile=str(CERTFILE),
    )
