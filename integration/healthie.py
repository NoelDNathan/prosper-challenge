"""Healthie EHR integration module.

This module provides functions to interact with Healthie for patient management
and appointment scheduling.
"""

import os
import time
from playwright.async_api import (
    TimeoutError,
    async_playwright,
    Browser,
    Locator,
    Page,
)

from utils.get_verification_code import get_otp
from utils.playwright_helpers import (
    _wait_for_test_id, 
    get_value_by_label, 
    get_text, 
    ensure_section_open,
)

from loguru import logger

_browser: Browser | None = None
_page: Page | None = None

DEFAULT_WAIT_TIME = 10000
MAX_WAIT_TIME = 30_000


async def login_to_healthie() -> Page:
    """Log into Healthie and return an authenticated page instance.

    This function handles the login process using credentials from environment
    variables. The browser and page instances are stored for reuse by other
    functions in this module.

    Returns:
        Page: An authenticated Playwright Page instance ready for use.

    Raises:
        ValueError: If required environment variables are missing.
        Exception: If login fails for any reason.
    """
    global _browser, _page

    email = os.environ.get("HEALTHIE_EMAIL")
    password = os.environ.get("HEALTHIE_PASSWORD")

    if not email or not password:
        raise ValueError("HEALTHIE_EMAIL and HEALTHIE_PASSWORD must be set in environment variables")

    if _page is not None:
        logger.info("Using existing Healthie session")
        return _page

    logger.info("Logging into Healthie...")
    playwright = await async_playwright().start()
    _browser = await playwright.chromium.launch(headless=False)
    
    context = await _browser.new_context(viewport={"width": 1920, "height": 1080}
)
    _page = await context.new_page()
    _page.set_default_navigation_timeout(DEFAULT_WAIT_TIME)

    await _page.goto("https://secure.gethealthie.com/users/sign_in", wait_until="domcontentloaded")
    
    # Wait for the email input to be visible
    email_input = _page.locator('input[name="identifier"], [data-test-id="input-identifier"]')
    await email_input.wait_for(state="visible", timeout=30000)
    await email_input.fill(email)

    submit_button = _page.locator('button:has-text("Log In")')
    await submit_button.wait_for(state="visible", timeout=30000)
    await submit_button.click()
    
    # Wait for password input
    password_input = _page.locator('input[name="password"]')
    await password_input.wait_for(state="visible", timeout=30000)
    await password_input.fill(password)
    
    # Find and click the Log In button
    submit_button = _page.locator('button:has-text("Log In")')
    await submit_button.wait_for(state="visible", timeout=30000)
    await submit_button.click()
    
    time.sleep(10)
    otp_code = get_otp(subject_filter="Sign-in verification code")
    logger.info(f"OTP: {otp_code}")


    for i, digit in enumerate(otp_code):
        await _page.locator(f'div[data-test-id="otc-input-{i}"] input').fill(digit)

    # otc_inputs = _page.get_by_test_id("otc-box")
    # await otc_inputs.wait_for(state="visible", timeout=30000)
    # Wait for navigation after login
    
    # Check if we've navigated away from the sign-in page
    current_url = _page.url
    if "sign_in" in current_url:
        raise Exception("Login may have failed - still on sign-in page")

    logger.info("Successfully logged into Healthie")
    return _page



async def find_patient(name: str, date_of_birth: str) -> dict | None:
    """Find a patient in Healthie by name and date of birth.

    Args:
        name: The patient's full name.
        date_of_birth: The patient's date of birth in a format that Healthie accepts.

    Returns:
        dict | None: A dictionary containing patient information if found,
            including at least a 'patient_id' field. Returns None if the patient
            is not found or if an error occurs.

    Example return value:
        {
            "patient_id": "12345",
            "name": "John Doe",
            "date_of_birth": "1990-01-15",
            ...
        }
    """
    page = await login_to_healthie()
    logger.info(f"Searching Healthie for {name} (DOB: {date_of_birth})")

    try:
        clients_link = page.get_by_role("link", name="Clients")
        await clients_link.wait_for(state="visible", timeout=MAX_WAIT_TIME)
        await clients_link.click()

        search_input = await _wait_for_test_id(page, "search-input")
        await search_input.fill(name)
        await search_input.press("Enter")
        await page.wait_for_timeout(3000)
        

        no_results_text = page.get_by_text("No results match your search", exact=False)
        try:
            await no_results_text.wait_for(state="visible", timeout=2000)
            logger.info("No results message displayed for %s", name)
            return None
        except TimeoutError:
            pass

        results_container = page.locator("#quick-profile-user-list-target")
        try:
            await results_container.wait_for(state="visible", timeout=MAX_WAIT_TIME)
            await results_container.locator("table").wait_for(
                state="visible", timeout=MAX_WAIT_TIME
            )
        except TimeoutError:
            html = await page.inner_html()
            logger.warning(
                "Results container did not become visible for %s. Assuming no matches.",
                name,
            )
            logger.debug("Page snippet:\n%s", html[:1000])
            return None

        user_rows = results_container.get_by_test_id("user-row")
        num_user_rows = await user_rows.count()
        logger.info(f"User rows found for {name}: {num_user_rows}")

        if num_user_rows == 0:
            logger.error(f"No matching patient rows found for {name}.")
            return None

        if num_user_rows > 1:
            logger.warning(
                f"Multiple ({num_user_rows}) patients found for {name}; using the first result"
            )

        first_user_row = user_rows.nth(0)
        await first_user_row.wait_for(state="visible", timeout=MAX_WAIT_TIME)

        first_user_link = first_user_row.get_by_test_id("client-link")
        await first_user_link.wait_for(state="visible", timeout=MAX_WAIT_TIME)
        await first_user_link.click()
        await page.wait_for_timeout(1500)

        section = page.get_by_test_id("cp-section-basic-information")
        await ensure_section_open(section)

        basic_info = page.get_by_test_id("client-basic-info")
        await basic_info.wait_for(state="visible", timeout=MAX_WAIT_TIME)

        user_unique_id = await get_text(basic_info, "unique-client-id")
        client_since = await get_text(basic_info, "client-since")
        date_of_birth_extracted = await get_text(basic_info, "client-dob")
        phone_number = await get_value_by_label(basic_info, "Phone number")
        group = await get_value_by_label(basic_info, "Group")
        timezone = await get_value_by_label(basic_info, "Timezone")
        location = await get_value_by_label(basic_info, "Location")
        last_fitbit_sync = await get_value_by_label(basic_info, "Last Fitbit sync")

        email_element = page.locator(".sidebar-email")
        email = (await email_element.text_content() or "").strip()
    except Exception as exc:
        logger.exception(f"Failed to retrieve patient {name} from Healthie: {exc}")
        return None

    user_data = {
        "user_unique_id": user_unique_id,
        "name": name,
        "email": email,
        "phone_number": phone_number,
        "group": group,
        "date_of_birth": date_of_birth_extracted or date_of_birth,
        "current_weight": None,
        "current_height": None,
        "location": location,
        "timezone": timezone,
        "last fitbit sync": last_fitbit_sync,
        "client_since": client_since,
    }

    logger.info(f"Returning data for client {name} (ID {user_unique_id})")
    return user_data
    
  

async def create_appointment(patient_id: str, date: str, time: str) -> dict | None:
    """Create an appointment in Healthie for the specified patient.

    Args:
        patient_id: The unique identifier for the patient in Healthie.
        date: The desired appointment date in a format that Healthie accepts.
        time: The desired appointment time in a format that Healthie accepts.

    Returns:
        dict | None: A dictionary containing appointment information if created
            successfully, including at least an 'appointment_id' field.
            Returns None if appointment creation fails.

    Example return value:
        {
            "appointment_id": "67890",
            "patient_id": "12345",
            "date": "2026-02-15",
            "time": "10:00 AM",
            ...
        }
    """
    # TODO: Implement appointment creation functionality using Playwright
    # 1. Ensure you're logged in by calling login_to_healthie()
    # 2. Navigate to the appointment creation page for the patient
    # 3. Fill in the date and time fields
    # 4. Submit the appointment creation form
    # 5. Verify the appointment was created successfully
    # 6. Return appointment information
    # 7. Handle errors (e.g., time slot unavailable, invalid date/time)
    pass
