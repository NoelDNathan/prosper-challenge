"""
Test the Healthie live integration.
"""

import os

import pytest
import pytest_asyncio

import integration.healthie as healthie
from tests.conftest import _ensure_credentials

LIVE_PATIENT_NAME = "Noel Nathan Planell Bosch"
LIVE_PATIENT_DOB = "Aug 28, 2003"
LIVE_PATIENT_EMAIL = "noelchorradas@gmail.com"
LIVE_PATIENT_PHONE = "611543543"
LIVE_CLIENT_ID = "13632834"
LIVE_GROUP = "No Group"
LIVE_LAST_SYNC = "Sync Not Set Up"
LIVE_CLIENT_SINCE = "Feb 18, 2026"


LIVE_PATIENT_ID = "13632834"


@pytest_asyncio.fixture(scope="function")
async def authenticated_healthie_session():
    """Authenticate the Healthie session."""
    _ensure_credentials()
    page = await healthie.login_to_healthie()
    yield page
    browser = getattr(healthie, "_browser", None)
    if browser:
        await browser.close()
    healthie._browser = None
    healthie._page = None


@pytest.mark.asyncio
@pytest.mark.live
async def test_find_patient_live_returns_expected(authenticated_healthie_session):
    """Validate that find_patient() returns the expected fields for a known client."""
    patient = await healthie.find_patient(LIVE_PATIENT_NAME, LIVE_PATIENT_DOB)
    assert patient is not None, "Expected to find the live Healthie patient"
    assert patient["user_unique_id"] == LIVE_CLIENT_ID
    assert patient["name"] == LIVE_PATIENT_NAME
    assert patient["email"] == LIVE_PATIENT_EMAIL
    assert patient["phone_number"] == LIVE_PATIENT_PHONE
    assert patient["group"] == LIVE_GROUP
    assert patient["date_of_birth"] == LIVE_PATIENT_DOB
    assert patient["last fitbit sync"] == LIVE_LAST_SYNC
    assert patient["client_since"] == LIVE_CLIENT_SINCE


@pytest.mark.asyncio
@pytest.mark.live
async def test_find_patient_live_handles_missing(authenticated_healthie_session):
    """Ensure that searching for a nonexistent patient returns None."""
    missing_patient = await healthie.find_patient("No Such Patient 99999", "1900-01-01")
    assert missing_patient is None

@pytest.mark.asyncio
@pytest.mark.live
async def test_create_appointment_success(authenticated_healthie_session):
    """Validate that create_appointment() returns the expected fields for a known client."""
    appointment = await healthie.create_appointment(LIVE_PATIENT_ID, "2026-02-28", "12:00 PM")
    assert appointment is not None, "Expected to create an appointment for the live Healthie patient"


@pytest.mark.asyncio
@pytest.mark.live
async def test_create_appointment_another_event_scheduled_at_this_time(authenticated_healthie_session):
    """Validate that create_appointment() returns the expected fields for a known client."""
    appointment = await healthie.create_appointment(LIVE_PATIENT_ID, "2026-02-27", "10:00 AM")
    assert appointment is not None, "Expected to create an appointment for the live Healthie patient"
    appointment2 = await healthie.create_appointment(LIVE_PATIENT_ID, "2026-02-27", "10:00 AM")
    assert appointment2 is  None, "Other event scheduled at this time"



@pytest.mark.asyncio
@pytest.mark.live
async def test_create_appointment_invalid_date_format(authenticated_healthie_session):
    """Validate that create_appointment() returns the expected fields for a known client."""
    appointment = await healthie.create_appointment(LIVE_PATIENT_ID, "02-20-2026", "10:00 AM")
    assert appointment is  None, "Invalid date format"


@pytest.mark.asyncio
@pytest.mark.live
async def test_create_appointment_invalid_date_is_in_the_past(authenticated_healthie_session):
    """Validate that create_appointment() returns the expected fields for a known client."""
    appointment = await healthie.create_appointment(LIVE_PATIENT_ID, "2026-02-19", "10:00 AM")
    assert appointment is  None, "Date is in the past"
