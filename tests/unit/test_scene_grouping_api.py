from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db.session import Base, SessionLocal, engine
from app.main import app
from app.models.entities import ImageAsset, Project

client = TestClient(app)


@pytest.fixture(autouse=True)
def init_db():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


def test_group_project_scenes_endpoint():
    db = SessionLocal()
    try:
        project = Project(name="Scene Grouping Test")
        db.add(project)
        db.flush()

        asset1 = ImageAsset(
            project_id=project.id,
            filename="img1.jpg",
            storage_uri="local://test/img1.jpg",
            sha256="hash1",
        )
        asset2 = ImageAsset(
            project_id=project.id,
            filename="img2.jpg",
            storage_uri="local://test/img2.jpg",
            sha256="hash2",
        )
        db.add(asset1)
        db.add(asset2)
        db.commit()
        project_id = project.id
    finally:
        db.close()

    resp = client.post(f"/api/v1/projects/{project_id}/group-scenes")
    assert resp.status_code == 200
    data = resp.json()
    assert "groups" in data
    assert "unresolved" in data
    assert "diagnostics" in data
    # When no pairwise matches exist, images are unresolved rather than faking geometric connection
    assert len(data["unresolved"]) == 2
    assert data["diagnostics"]["image_count"] == 2
