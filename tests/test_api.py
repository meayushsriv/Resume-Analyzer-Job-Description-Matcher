# Location: /tests/test_api.py

import pytest
import pytest_asyncio
import httpx
import io
from fastapi import status
import time

# ... (pytestmark and BASE_URL are unchanged) ...
pytestmark = pytest.mark.asyncio
BASE_URL = "http://api:8000"

# ... (client fixture is unchanged) ...
@pytest_asyncio.fixture(scope="function")
async def client():
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        yield client

# ... (test_health_check is unchanged and passing) ...
async def test_health_check(client: httpx.AsyncClient):
    response = await client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok", "message": "API is healthy"}


async def test_upload_resume(client: httpx.AsyncClient, mocker):
    """
    Test 2: The most important test.
    ...
    """
    
    mock_parse_task = mocker.patch("src.api.v1.endpoints.resumes.parse_resume_task")

    # --- THIS IS THE FIX ---
    # We add a timestamp to the file content to make its
    # hash unique for every single test run.
    fake_file_content = f"This is a fake PDF content {time.time()}".encode("utf-8")
    # -----------------------
    
    fake_file = io.BytesIO(fake_file_content)
    
    # --- AND WE GIVE THE FILE A UNIQUE NAME ---
    file_name = f"test_resume_{time.time()}.pdf"
    # ----------------------------------------
    
    response = await client.post(
        "/api/v1/resumes/upload",
        files={"file": (file_name, fake_file, "application/pdf")} # <-- Use new unique name
    )
    
    # 4. Check the API response
    assert response.status_code == status.HTTP_200_OK # This will now pass
    response_data = response.json()
    assert response_data["status"] == "pending"
    assert "id" in response_data
    assert response_data["message"] == "Resume uploaded successfully, queued for processing."
    
    # 5. Check if our mock Celery task was called
    mock_parse_task.delay.assert_called_once()
    mock_parse_task.assert_called_with(response_data["id"])


# ... (test_upload_file_too_large is unchanged and passing) ...
async def test_upload_file_too_large(client: httpx.AsyncClient):
    """
    Test 3: Does our 10MB file size limit work?
    """
    fake_large_file_content = b"A" * (11 * 1024 * 1024)
    fake_large_file = io.BytesIO(fake_large_file_content)
    
    response = await client.post(
        "/api/v1/resumes/upload",
        files={"file": ("large_file.pdf", fake_large_file, "application/pdf")}
    )
    
    assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    
    response_data = response.json()
    assert "File size exceeds 10MB limit" in response_data["detail"]