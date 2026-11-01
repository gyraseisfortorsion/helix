import pytest
from fastapi.testclient import TestClient

from api.config import Settings
from api.main import create_app
from api.store import Store


@pytest.fixture
def store(tmp_path):
    return Store(
        Settings(
            dna_data_dir=tmp_path,
            anthropic_api_key="",
            alphagenome_api_key="",
            evo2_base_url="",
            evo2_forward_url="",
            evo2_access_token="",
        )
    )


@pytest.fixture
def client(tmp_path):
    config = Settings(
        dna_data_dir=tmp_path,
        anthropic_api_key="",
        alphagenome_api_key="",
        evo2_base_url="",
        evo2_forward_url="",
        evo2_access_token="",
    )
    with TestClient(create_app(config)) as instance:
        yield instance


def demo_session(client):
    response = client.post("/api/session", json={"demo": True, "demo_source": "synthetic"})
    assert response.status_code == 200
    value = response.json()
    return value, {"Authorization": "Bearer " + value["token"]}
