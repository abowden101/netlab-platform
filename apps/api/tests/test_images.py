"""BYO image upload tests."""

import hashlib
import io

FAKE_TAR = b"fake-tarball-content" * 100


def test_upload_requires_auth(client):
    resp = client.post(
        "/api/v1/images/upload",
        files={"file": ("ios-xe.tar", io.BytesIO(FAKE_TAR))},
        data={"vendor": "cisco", "license_acknowledged": "true"},
    )
    assert resp.status_code == 401


def test_upload_without_license_ack_refused(student_headers, client):
    resp = client.post(
        "/api/v1/images/upload",
        files={"file": ("ios-xe.tar", io.BytesIO(FAKE_TAR))},
        data={"vendor": "cisco", "license_acknowledged": "false"},
        headers=student_headers,
    )
    assert resp.status_code == 400
    assert "license acknowledgement" in resp.json()["detail"]


def test_upload_non_tar_refused(student_headers, client):
    resp = client.post(
        "/api/v1/images/upload",
        files={"file": ("ios-xe.iso", io.BytesIO(FAKE_TAR))},
        data={"vendor": "cisco", "license_acknowledged": "true"},
        headers=student_headers,
    )
    assert resp.status_code == 400


def test_upload_tar_with_ack_succeeds(student_headers, client):
    resp = client.post(
        "/api/v1/images/upload",
        files={"file": ("ios-xe.tar", io.BytesIO(FAKE_TAR))},
        data={"vendor": "cisco", "license_acknowledged": "true"},
        headers=student_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["sha256"] == hashlib.sha256(FAKE_TAR).hexdigest()
    assert body["image_ref"].startswith("byo:")
    assert body["size_bytes"] == len(FAKE_TAR)
    assert "proprietary" in body["license_notice"]


def test_list_images(student_headers, client):
    resp = client.get("/api/v1/images", headers=student_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
