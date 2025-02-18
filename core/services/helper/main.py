#!/usr/bin/env python3

import http
from functools import cache
from pathlib import Path
from typing import Any, List, Optional

import psutil
import requests
import uvicorn
from bs4 import BeautifulSoup
from commonwealth.utils.apis import GenericErrorHandlingRoute, PrettyJSONResponse
from commonwealth.utils.decorators import temporary_cache
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi_versioning import VersionedFastAPI, version
from pydantic import BaseModel

PORT = 81
DOCS_CANDIDATE_URLS = ["/docs", "/v1.0/ui/"]
API_CANDIDATE_URLS = ["/docs.json", "/openapi.json", "/swagger.json"]

HTML_FOLDER = Path.joinpath(Path(__file__).parent.absolute(), "html")


class ServiceMetadata(BaseModel):
    name: str
    description: str
    icon: str
    company: str
    version: str
    webpage: str
    api: str


class ServiceInfo(BaseModel):
    valid: bool
    title: str
    documentation_url: str
    versions: List[str]
    port: int
    metadata: Optional[ServiceMetadata]


class Helper:
    LOCALSERVER_CANDIDATES = ["0.0.0.0", "::"]

    @staticmethod
    @cache
    def detect_service(port: int) -> ServiceInfo:
        info = ServiceInfo(valid=False, title="Unknown", documentation_url="", versions=[], port=port)

        try:
            with requests.get(f"http://127.0.0.1:{port}/", timeout=0.2) as response:
                info.valid = True
                soup = BeautifulSoup(response.text, features="html.parser")
                title_element = soup.find("title")
                info.title = title_element.text if title_element else "Unknown"
        except Exception:
            # The server is not available, any error code will be handle by the 'with' block
            pass

        # If not valid web server, documentation will not be available
        if not info.valid:
            return info

        # Check for service description metadata
        try:
            with requests.get(f"http://127.0.0.1:{port}/register_service", timeout=0.2) as response:
                if response.status_code == http.HTTPStatus.OK:
                    info.metadata = ServiceMetadata.parse_obj(response.json())
        except Exception:
            # This should be avoided by the first try block, but better safe than sorry
            pass

        for documentation_path in DOCS_CANDIDATE_URLS:
            try:
                with requests.get(f"http://127.0.0.1:{port}{documentation_path}", timeout=0.2) as response:
                    if response.status_code != http.HTTPStatus.OK:
                        continue
                    info.documentation_url = documentation_path

                # Get main openapi json description file
                for api_path in API_CANDIDATE_URLS:
                    with requests.get(f"http://127.0.0.1:{port}{api_path}", timeout=0.2) as response:
                        if response.status_code != http.HTTPStatus.OK:
                            continue
                        api = response.json()
                        # Check all available versions
                        ## The ones that provide a swagger-ui
                        for path in api["paths"].keys():
                            with requests.get(f"http://127.0.0.1:{port}{path}", timeout=0.2) as response:
                                if "swagger-ui" in response.text:
                                    info.versions += [path]
                break

            except Exception:
                # This should be avoided by the first try block, but better safe than sorry
                break
        return info

    @staticmethod
    @temporary_cache(timeout_seconds=10)
    def scan_ports() -> List[ServiceInfo]:
        # Filter for TCP ports that are listen and can be accessed by external users (server in 0.0.0.0)
        connections = (
            connection
            for connection in psutil.net_connections("tcp")
            if connection.status == psutil.CONN_LISTEN and connection.laddr.ip in Helper.LOCALSERVER_CANDIDATES
        )

        # And check if there is a webpage available that is not us
        # Use it as a set to remove duplicated ports
        ports = set(connection.laddr.port for connection in connections)
        services = (Helper.detect_service(port) for port in ports if port != PORT)
        return [service for service in services if service.valid]


fast_api_app = FastAPI(
    title="Helper API",
    description="Everybody's helper to find web services that are running in BlueOS.",
    default_response_class=PrettyJSONResponse,
)
fast_api_app.router.route_class = GenericErrorHandlingRoute


@fast_api_app.get(
    "/web_services",
    response_model=List[ServiceInfo],
    summary="Retrieve web services found.",
)
@version(1, 0)
def web_services() -> Any:
    """REST API endpoint to retrieve web services running."""
    return Helper.scan_ports()


app = VersionedFastAPI(
    fast_api_app,
    version="1.0.0",
    prefix_format="/v{major}.{minor}",
    enable_latest=True,
)

app.mount("/", StaticFiles(directory=str(HTML_FOLDER), html=True))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
