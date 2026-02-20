"""Pipecat Healthie adapter module.

This module provides functions to interact with Healthie for patient management
and appointment scheduling using Pipecat.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from integration import healthie
from pipecat.services.llm_service import FunctionCallParams
from utils.date_helpers import convert_to_datetime
from loguru import logger



DATE_INPUT_FORMATS = ("%Y-%m-%d", "%b %d, %Y", "%B %d, %Y")


def _parse_flexible_date(value: str) -> datetime:
    trimmed = value.strip()
    last_error: Exception | None = None
    for fmt in DATE_INPUT_FORMATS:
        try:
            return datetime.strptime(trimmed, fmt)
        except ValueError as exc:  # noqa: BLE001
            last_error = exc
    raise ValueError(
        f"Date '{value}' must match one of the formats: {', '.join(DATE_INPUT_FORMATS)}"
    ) from last_error


def _build_error_payload(message: str, code: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"success": False, "error": message}
    if code:
        payload["error_code"] = code
    return payload


async def _respond_with_error(params: FunctionCallParams, message: str, code: str | None = None):
    await params.result_callback(_build_error_payload(message, code))


@dataclass
class PatientAppointmentRequest:
    patient_name: str
    patient_date_of_birth: str
    appointment_date: str
    appointment_time: str

    def __post_init__(self):
        self.patient_name = self.patient_name.strip()
        if not self.patient_name:
            raise ValueError("Patient name cannot be empty.")

    def normalized_dob(self) -> str:
        return _parse_flexible_date(self.patient_date_of_birth).strftime("%Y-%m-%d")

    def appointment_datetime(self) -> datetime:
        return convert_to_datetime(
            self.appointment_date.strip(), self.appointment_time.strip()
        )


@dataclass
class FindPatientRequest:
    """Request to find a patient in Healthie by name and date of birth."""
    patient_name: str
    patient_date_of_birth: str


@dataclass
class CreateAppointmentRequest:
    patient_id: str
    appointment_date_iso: str
    appointment_time_formatted: str

async def find_patient_direct(
    params: FunctionCallParams,
    patient_name: str,
    patient_date_of_birth: str,
) -> None:
    """Find a patient in Healthie by name and date of birth.

    Args:
        params: The function call parameters.
        patient_name: The patient's full name. Example: Noel Nathan Planell Bosch
        patient_date_of_birth: The patient's date of birth in a format that Healthie accepts. Example: Aug 28, 2003
        
    """

    try:
        request = FindPatientRequest(
            patient_name=patient_name,
            patient_date_of_birth=patient_date_of_birth,
        )
        patient = await healthie.find_patient(request.patient_name, request.patient_date_of_birth)
        if patient is None:
            await _respond_with_error(params, "No patient found for the given name and date of birth.", "patient_not_found")
            return
        patient_id = patient.get("patient_id")
        if not patient_id:
            await _respond_with_error(params, "Patient record is missing an identifier; cannot find a patient.", "patient_id_not_found")
            return
        result_payload = {
            "success": True,
            "patient": {
                "id": patient_id,
                "name": patient.get("name", request.patient_name),
                "email": patient.get("email"),
                "phone_number": patient.get("phone_number"),
            },
        }
        await params.result_callback(result_payload)
    except ValueError as exc:
        await _respond_with_error(params, str(exc), "invalid_input")


async def create_appointment_direct(
    params: FunctionCallParams,
    patient_id: str,
    appointment_date: str,
    appointment_time: str,
):
    """Schedule a Healthie appointment once patient and slot details are available.
    
    Args:
        params: The function call parameters.
        patient_id: The unique identifier for the patient in Healthie.
        appointment_date: The desired appointment date in a format that Healthie accepts. Example: 2026-02-27
        appointment_time: The desired appointment time in a format that Healthie accepts. Example: 10:00 AM
    """
    try:
        request = CreateAppointmentRequest(
            patient_id=patient_id,
            appointment_date_iso=appointment_date,
            appointment_time_formatted=appointment_time,
        )
        appointment = await healthie.create_appointment(request.patient_id, request.appointment_date_iso, request.appointment_time_formatted)
        if appointment is None:
            await _respond_with_error(params, "Healthie rejected the appointment request; please try another slot.", "appointment_creation_failed")
            return
        result_payload = {
            "success": True,
            "appointment": appointment,
        }
        await params.result_callback(result_payload)
    except ValueError as exc:
        await _respond_with_error(params, str(exc), "invalid_input")
    except Exception as exc:
        await _respond_with_error(params, str(exc), "unexpected_error")
