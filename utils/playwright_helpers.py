"""
Playwright helpers.
"""
from playwright.async_api import Page, Locator

MAX_WAIT_TIME = 30_000

async def _wait_for_test_id(page: Page, test_id: str) -> Locator:
    """Wait for a control identified by a test ID to be visible before returning it."""
    locator = page.get_by_test_id(test_id)
    await locator.wait_for(state="visible", timeout=MAX_WAIT_TIME)
    return locator


async def get_value_by_label(container: Locator, label_text: str) -> str:
    """Get the value of a label in a container. 
    Args:
        container: The container to search for the label.
        label_text: The text of the label to search for.

    Returns:
        str: The value of the label.
    """

    row = container.locator("div.row").filter(has_text=label_text)
    return await row.locator("div").last.inner_text()

async def get_text(element: Locator, test_id: str) -> str | None:
    """Retrieve inner text from a test_id, safely."""
    return (await element.get_by_test_id(test_id).inner_text()).strip()

async def ensure_section_open(section: Locator) -> None:
    """Click to open a collapsible section if not already opened."""
    classes = (await section.get_attribute("class")) or ""
    if "opened" not in classes:
        await section.get_by_role("button").click()