from datetime import datetime


def convert_to_datetime(date: str, time: str) -> datetime:
    """
    Convert a date and time string to a datetime object.
    Args:
        date: str: ''YYYY-MM-DD'
        time: str: 'HH:MM AM/PM'
    Returns:
        datetime: The datetime object.
    """
    return datetime.strptime(f"{date} {time}", "%Y-%m-%d %I:%M %p")


def format_target_date(date, time):
    """
    Args:
        date: str: 'YYYY-MM-DD'
        time: str: 'HH:MM AM/PM'
    Returns:
        str: 'Saturday, February 28th'
    """

    def day_with_suffix(day: int) -> str:
        if 11 <= day <= 13:
            return f"{day}th"
        last_digit = day % 10
        if last_digit == 1:
            return f"{day}st"
        elif last_digit == 2:
            return f"{day}nd"
        elif last_digit == 3:
            return f"{day}rd"
        return f"{day}th"

    target = convert_to_datetime(date, time)
    day_str = day_with_suffix(target.day)
    formatted = target.strftime(f"%A, %B {day_str}")
    return formatted


def calculate_diff_months(now: datetime, target_datetime: datetime) -> int:
    """
    Calculate the difference in months between two dates.
    Args:
        now: datetime: The current date and time.
        target_datetime: datetime: The target date and time.
    Returns:
        int: The difference in months between the two dates.
    """
    if target_datetime < now:
        return 0
    diff_years = target_datetime.year - now.year
    diff_months = target_datetime.month - now.month

    total_months = diff_years * 12 + diff_months
    return total_months


def format_appointment_label(target: datetime) -> str:
    """
    Format the appointment label for Healthie.
    Args:
        target: datetime: The target date and time.
    Returns:
        str: 'Feb 28, 2026 at 4:00 PM'
    """
    fmt_time = target.strftime("%I:%M %p").lstrip("0")
    label = target.strftime(f"%b %d, %Y at {fmt_time}")
    return label
