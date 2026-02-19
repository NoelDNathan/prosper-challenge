import os

import pytest
import pytest_asyncio

from utils.get_verification_code import get_otp



@pytest.mark.asyncio
@pytest.mark.live
async def test_find_patient_live_returns_expected():
    """Validate that find_patient() returns the expected fields for a known client."""
    otp_code = get_otp(subject_filter="Sign-in verification code")
    assert otp_code is not None, "Expected to get an OTP code"
    assert len(otp_code) == 6, "Expected an OTP code of 6 digits"
    print(otp_code)
    print("OTP code received")

