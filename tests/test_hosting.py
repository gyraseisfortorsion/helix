from fastapi.testclient import TestClient

from api.config import Settings
from api.main import create_app


def test_hosted_frontend_cors_allows_authorization_and_rejects_other_origins(tmp_path):
    config = Settings(
        _env_file=None,
        dna_data_dir=tmp_path,
        dna_cors_origins="https://helix-lime-nine.vercel.app",
    )
    with TestClient(create_app(config, embedded_worker=False)) as client:
        headers = {
            "Origin": "https://helix-lime-nine.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        }
        response = client.options("/api/session", headers=headers)
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == headers["Origin"]
        response = client.options("/api/session", headers={**headers, "Origin": "https://other.example"})
        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers


def test_vps_private_workspace_requires_key_even_from_loopback(tmp_path):
    config = Settings(
        _env_file=None,
        dna_data_dir=tmp_path,
        dna_allow_local_workspaces=False,
        dna_access_key="deployment-test-access-key",
    )
    with TestClient(create_app(config, embedded_worker=False)) as client:
        response = client.post(
            "/api/session",
            json={"demo": False},
            headers={"X-Forwarded-For": "127.0.0.1"},
        )
        assert response.status_code == 403
        response = client.post(
            "/api/session", json={"demo": False, "access_key": "deployment-test-access-key"}
        )
        assert response.status_code == 200
        assert response.json()["demo"] is False
