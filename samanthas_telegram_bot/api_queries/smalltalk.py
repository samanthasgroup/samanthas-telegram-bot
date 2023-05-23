"""Functions for interaction with SmallTalk oral test service."""
import json
import logging
import os

import httpx

logger = logging.getLogger(__name__)

URL_PREFIX = "https://app.smalltalk2.me/api/integration"

HEADERS = {"Authorization": f"Bearer {os.environ.get('SMALLTALK_TOKEN')}"}
TEST_ID = os.environ.get("SMALLTALK_TEST_ID")


async def send_user_data_get_smalltalk_test(
    first_name: str,
    last_name: str,
    email: str,
) -> tuple[str | None, str | None]:
    """Gets Smalltalk interview ID and test URL."""

    async with httpx.AsyncClient() as client:
        r = await client.post(
            url=f"{URL_PREFIX}/send_test",
            headers=HEADERS,
            json={
                "test_id": TEST_ID,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
            },  # TODO possibly webhook
        )

    logger.debug(f"Request headers: {r.request.headers}, request content: {r.request.content}")
    data = json.loads(r.content)
    logger.debug(f"Response: {r.status_code=}, {r.headers=}, {r.content=}, {data=}")

    url = data.get("test_link", None)
    if url is None:
        logger.error("No oral test URL received")
        return None, None

    logger.info(f"Received URL to oral test: {url}")

    return data["interview_id"], url


async def get_smalltalk_result(test_id: str) -> dict[str, str] | None:
    """Gets results of Smalltalk interview."""

    # TODO arrange for some retries? Or just wait until we set up a webhook?
    async with httpx.AsyncClient() as client:
        r = await client.get(
            url=f"{URL_PREFIX}/test_status",
            headers=HEADERS,
            params={
                "id": test_id,
                "additional_fields": (
                    "detailed_scores,strength_weaknesses,problem_statuses,problem_titles"
                ),
            },
        )

    logger.debug(f"Request headers: {r.request.headers}, request content: {r.request.content}")
    data = json.loads(r.content)
    logger.debug(f"Response: {r.status_code=}, {r.headers=}, {r.content=}, {data=}")
    logger.info(f"Status: {data.get('status', None)}, score: {data.get('score', None),}")

    return data
