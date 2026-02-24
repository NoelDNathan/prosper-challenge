"""Healthie EHR integration module.

This module provides functions to interact with Healthie for patient management
and appointment scheduling.
"""

import os
import re
import time
from playwright.async_api import (
    Browser,
    Page,
    Playwright,
    TimeoutError,
    async_playwright,
)
from loguru import logger
from datetime import datetime

from utils.get_verification_code import get_otp
from utils.playwright_helpers import (
    _wait_for_test_id,
    get_value_by_label,
    get_text,
    ensure_section_open,
)

from utils.date_helpers import (
    calculate_diff_months,
    convert_to_datetime,
    format_target_date,
    format_appointment_label,
)

import asyncio 
_browser: Browser | None = None
_page: Page | None = None
_playwright: Playwright | None = None

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
    global _browser, _page, _playwright

    email = os.environ.get("HEALTHIE_EMAIL")
    password = os.environ.get("HEALTHIE_PASSWORD")

    if not email or not password:
        raise ValueError(
            "HEALTHIE_EMAIL and HEALTHIE_PASSWORD must be set in environment variables"
        )

    # if _page is not None:
    #     logger.info("Using existing Healthie session")
    #     return _page

    logger.info("Logging into Healthie...")
    _playwright = await async_playwright().start()
    _browser = await _playwright.chromium.launch(headless=False)

    context = await _browser.new_context(viewport={"width": 1920, "height": 1080})
    _page = await context.new_page()
    _page.set_default_navigation_timeout(DEFAULT_WAIT_TIME)

    await _page.goto(
        "https://secure.gethealthie.com/users/sign_in", wait_until="domcontentloaded"
    )

    # Wait for the email input to be visible
    email_input = _page.locator(
        'input[name="identifier"], [data-test-id="input-identifier"]'
    )
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
   
    continue_button = _page.locator("[data-test-id=\"passkeys-continue-to-app\"]")
    await continue_button.wait_for(state="visible", timeout=3000)
    if await continue_button.is_visible():
        await continue_button.click()
        return _page


    # -----------------------------------------------------------
    # If the continue button is not visible, we need to enter the OTP code
    # -----------------------------------------------------------
    
    await asyncio.sleep(10)
    otp_code = get_otp(subject_filter="Sign-in verification code")
    logger.info(f"OTP: {otp_code}")

    for i, digit in enumerate(otp_code):
        await _page.locator(f'div[data-test-id="otc-input-{i}"] input').fill(digit)

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
            "phone_number": "1234567890",
            "group": "Group 1",
            "timezone": "America/New_York",
            "location": "New York, NY",
            "last fitbit sync": "2026-01-01",
            "client_since": "2026-01-01",
        }
    """
    page = await login_to_healthie()
    logger.info(f"Searching Healthie for {name} (DOB: {date_of_birth})")

    try:

        # -----------------------------------------
        # Navigate to the Clients page
        # -----------------------------------------
        clients_link = page.get_by_role("link", name="Clients")
        await clients_link.wait_for(state="visible", timeout=MAX_WAIT_TIME)
        await clients_link.click()

        # -----------------------------------------
        # Search for the patient
        # -----------------------------------------
        search_input = await _wait_for_test_id(page, "search-input")
        await search_input.fill(name)
        await search_input.press("Enter")
        await page.wait_for_timeout(3000)

        # -----------------------------------------
        # Patient found or return None if not found
        # -----------------------------------------
        no_results_text = page.get_by_text("No results match your search", exact=False)
        try:
            await no_results_text.wait_for(state="visible", timeout=2000)
            logger.info(f"No results message displayed for {name}")
            return None
        except TimeoutError:
            pass

        # -----------------------------------------
        # Table of patients found
        # -----------------------------------------
        results_container = page.locator("#quick-profile-user-list-target")
        try:
            await results_container.wait_for(state="visible")
            await results_container.locator("table").wait_for(
                state="visible", timeout=MAX_WAIT_TIME
            )
        except TimeoutError:
            logger.warning(
                f"Results container did not become visible for {name}. Assuming no matches.",
            )
            return None

        # -----------------------------------------
        # Get the number of users found
        # -----------------------------------------
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

        # -----------------------------------------
        # Click on the first user row
        # -----------------------------------------
        first_user_row = user_rows.nth(0)
        await first_user_row.wait_for(state="visible", timeout=MAX_WAIT_TIME)

        first_user_link = first_user_row.get_by_test_id("client-link")
        await first_user_link.wait_for(state="visible", timeout=MAX_WAIT_TIME)
        await first_user_link.click()
        await page.wait_for_timeout(1500)

        # -----------------------------------------
        # Open the basic information section
        # -----------------------------------------
        section = page.get_by_test_id("cp-section-basic-information")
        await ensure_section_open(section)

        basic_info = page.get_by_test_id("client-basic-info")
        await basic_info.wait_for(state="visible")

        # -----------------------------------------
        # Extract the basic information
        # -----------------------------------------

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
        "patient_id": user_unique_id,
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
    logger.info(user_data)
    return user_data


async def create_appointment(
    patient_id: str, date_str: str, time_str: str
) -> dict | None:
    """Create an appointment in Healthie for the specified patient.

    Args:
        patient_id: The unique identifier for the patient in Healthie.
        date: /MM/DD/YYYY  The desired appointment date in a format that Healthie accepts.
        time: HH:MM AM/PM The desired appointment time in a format that Healthie accepts.

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

    # 1. Ensure you're logged in by calling login_to_healthie()
    # 2. Navigate to the appointment creation page for the patient
    # 3. Fill in the date and time fields
    # 4. Submit the appointment creation form
    # 5. Verify the appointment was created successfully
    # 6. Return appointment information
    # 7. Handle errors (e.g., time slot unavailable, invalid date/time)

    _page = await login_to_healthie()

    try:
        # -----------------------------------------
        # Search for the patient profile
        # -----------------------------------------
        search_input = await _wait_for_test_id(_page, "header-client-search-form")
        await search_input.fill(patient_id)
        await search_input.press("Enter")
        await _page.wait_for_timeout(3000)

        view_profile = await _wait_for_test_id(_page, "view-profile")
        await view_profile.wait_for(state="visible")
        await view_profile.click()

        # -----------------------------------------
        # Open the Create Appointment
        # -----------------------------------------
        add_appointment_button = await _wait_for_test_id(
            _page, "add-appointment-button"
        )
        await add_appointment_button.wait_for(state="visible")
        await add_appointment_button.click()

        appointment_modal = _page.locator(
            "div._asideModalBody_bk67x_39, div[data-test-id='appointment-modal-body']"
        )
        await appointment_modal.wait_for(state="visible")

        # -----------------------------------------
        # Validate if the appointment is in the past
        # -----------------------------------------
        await _page.locator(
            ".appointment_type_id > .css-1wpuca6-control > .css-cjz6q7 > .css-qc71lm"
        ).click()
        await _page.get_by_text("Initial Consultation - 60 Minutes", exact=True).click()

        # -----------------------------------------
        # Validate if the appointment is not in the past or return None
        # -----------------------------------------
        now = datetime.now()

        appointment_datetime = convert_to_datetime(date_str, time_str)

        if appointment_datetime < now:
            # Cannot create appointment in the past"
            return None

        # -----------------------------------------
        # Select the appointment time
        # -----------------------------------------
        await _page.get_by_placeholder("Select a time").click()
        time_picker = _page.locator(
            "li.react-datepicker__time-list-item", has_text=time_str
        )
        await time_picker.wait_for(state="visible")
        await time_picker.click()
        await _page.wait_for_timeout(1000)

        await _page.get_by_role("textbox", name="Start date*").click()

        total_months = calculate_diff_months(now, appointment_datetime)
        for _ in range(total_months):
            await _page.get_by_test_id("next-month").click()

        await _page.get_by_role(
            "button", name=f"Choose {format_target_date(date_str, time_str)}"
        ).click()

        # -------------------------------------------------------------
        # Verify if there is no another event scheduled at this time or return None
        # -------------------------------------------------------------
        flash = _page.locator("div.flash-message")

        await asyncio.sleep(1)
        flash = _page.get_by_test_id("appointment-form-modal").get_by_test_id(
            "flash-message"
        )
        if await flash.is_visible():
            intent = await flash.inner_text()
            logger.info(f"Intent: {str(intent)}")
            if intent == "You have another event scheduled at this time":
                logger.info("Another event scheduled at this time")
                return None

        # -----------------------------------------
        # Create the appointment
        # -----------------------------------------
        await _page.get_by_test_id("appointment-form-modal").get_by_test_id(
            "primaryButton"
        ).click()

        # -----------------------------------------
        # Verify appointment was created successfully
        # -----------------------------------------
        # reload the appointments list
        await asyncio.sleep(0.5)
        await _page.get_by_test_id("tab-past").click()
        await asyncio.sleep(0.5)
        await _page.get_by_test_id("tab-future").click()
        await asyncio.sleep(2)

        appointments_list = _page.get_by_test_id(
            "cop-appointments-section"
        ).get_by_test_id("collapsible-section-body")
        await appointments_list.wait_for(state="visible")


        data_label = format_appointment_label(appointment_datetime)
        appointment_found = appointments_list.get_by_text(data_label, exact=False)
        if await appointment_found.is_visible():
            logger.info("Appointment found at this time")
            await appointment_found.click()
            await asyncio.sleep(5)
        else:
            logger.info(f"No appointment found at this time: {data_label}")
            return None

        # -----------------------------------------
        # Extract appointment data
        # -----------------------------------------
        link = _page.get_by_role("link", name="Healthie video call")
        meeting_link = await link.get_attribute("href")
        meeting_link = "https://secure.gethealthie.com/" + meeting_link
        logger.info(f"Link: {meeting_link}")


        appointment_data = {
            "patient_phone": "phone_text",
            "meeting_link": meeting_link,
            "consultation_type": "Initial Consultation",
            "consultation_duration": "60 Minutes",
            "patient_name": "patient_name",
            "appointment_channel": "video call",
            "appointment_date": date_str,
            "appointment_time": time_str,
        }
        logger.info(f"Created appointment data: {appointment_data}")
        return appointment_data

    except Exception as exc:
        logger.exception(f"Failed to search for patient {patient_id}: {exc}")
        return None


async def close_healthie_session() -> None:
    """Clean up any Playwright resources associated with the Healthie session."""
    global _browser, _page, _playwright

    if _browser is not None:
        await _browser.close()
        _browser = None

    if _playwright is not None:
        await _playwright.stop()
        _playwright = None

    _page = None
