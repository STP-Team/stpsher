import datetime
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from infrastructure.api.production_calendar import production_calendar
from infrastructure.database.models import Employee
from tgbot.misc.dicts import russian_months
from tgbot.services.schedule import ScheduleParser
from .pay_rates import PayRateService


@dataclass
class SalaryCalculationResult:
    """Result of salary calculation"""

    # Basic info
    user: Employee
    current_month_name: str
    current_year: int
    pay_rate: float

    # Working hours
    working_days: int
    total_working_hours: float
    regular_hours: float
    night_hours: float
    holiday_hours: float
    night_holiday_hours: float
    holiday_days_worked: List[str]

    # Additional shifts
    additional_shift_hours: float
    additional_shift_holiday_hours: float
    additional_shift_night_hours: float
    additional_shift_night_holiday_hours: float
    additional_shift_days_worked: List[str]

    # Salary components
    base_salary: float
    additional_shift_salary: float
    additional_shift_rate: float
    additional_shift_holiday_rate: float
    additional_shift_night_rate: float
    additional_shift_night_holiday_rate: float

    # Premiums
    csi_premium_amount: float
    flr_premium_amount: float
    gok_premium_amount: float
    target_premium_amount: float
    discipline_premium_amount: float
    tests_premium_amount: float
    thanks_premium_amount: float
    tutors_premium_amount: float
    head_adjust_premium_amount: float
    premium_amount: float

    # Final totals
    total_salary: float

    # Meta
    calculation_time: datetime.datetime
    premium_updated_at: Optional[datetime.datetime]


class SalaryCalculator:
    """Central service for salary calculations"""

    @staticmethod
    def _calculate_night_hours(
            start_hour: int, start_min: int, end_hour: int, end_min: int
    ) -> float:
        """Calculate night hours (22:00-06:00) from a work shift"""
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min

        # Handle overnight shifts
        if end_minutes < start_minutes:
            end_minutes += 24 * 60

        night_start = 22 * 60  # 22:00 in minutes
        night_end = 6 * 60  # 06:00 in minutes (next day)

        total_night_minutes = 0

        # Check for night hours in first day (22:00-24:00)
        first_day_night_start = night_start
        first_day_night_end = 24 * 60  # Midnight

        if start_minutes < first_day_night_end and end_minutes > first_day_night_start:
            overlap_start = max(start_minutes, first_day_night_start)
            overlap_end = min(end_minutes, first_day_night_end)
            if overlap_end > overlap_start:
                total_night_minutes += overlap_end - overlap_start

        # Check for night hours in second day (00:00-06:00)
        if end_minutes > 24 * 60:  # Shift continues to next day
            second_day_start = 24 * 60
            second_day_end = end_minutes
            second_day_night_start = 24 * 60  # 00:00 next day
            second_day_night_end = 24 * 60 + night_end  # 06:00 next day

            if (
                    second_day_start < second_day_night_end
                    and second_day_end > second_day_night_start
            ):
                overlap_start = max(second_day_start, second_day_night_start)
                overlap_end = min(second_day_end, second_day_night_end)
                if overlap_end > overlap_start:
                    total_night_minutes += overlap_end - overlap_start

        return total_night_minutes / 60  # Convert to hours

    @staticmethod
    async def _process_schedule_data(
            schedule_data: Dict[str, str],
            now: datetime.datetime,
            is_additional_shift: bool = False,
    ) -> Tuple[float, float, float, float, float, List[str]]:
        """Process schedule data and return working hours breakdown"""
        total_hours = 0.0
        night_hours = 0.0
        holiday_hours = 0.0
        night_holiday_hours = 0.0
        working_days = 0
        days_worked = []

        for day, schedule_time in schedule_data.items():
            if schedule_time and schedule_time not in ["Не указано", "В", "О"]:
                # Parse time format like "08:00-17:00"
                time_match = re.search(
                    r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})", schedule_time
                )
                if time_match:
                    start_hour, start_min, end_hour, end_min = map(
                        int, time_match.groups()
                    )
                    start_minutes = start_hour * 60 + start_min
                    end_minutes = end_hour * 60 + end_min

                    # Handle overnight shifts
                    if end_minutes < start_minutes:
                        end_minutes += 24 * 60

                    day_hours = (end_minutes - start_minutes) / 60

                    # Calculate night hours for this shift
                    shift_night_hours = SalaryCalculator._calculate_night_hours(
                        start_hour, start_min, end_hour, end_min
                    )

                    # For 12-hour shifts, subtract 1 hour for lunch break
                    if day_hours == 12:
                        day_hours = 11
                        # Adjust night hours proportionally if lunch break affects them
                        if shift_night_hours > 0:
                            shift_night_hours = shift_night_hours * (11 / 12)

                    # Check if this day is a holiday
                    try:
                        work_date = datetime.date(now.year, now.month, int(day))
                        is_holiday = await production_calendar.is_holiday(work_date)
                        holiday_name = await production_calendar.get_holiday_name(
                            work_date
                        )

                        if is_holiday and holiday_name:
                            holiday_hours += day_hours
                            night_holiday_hours += shift_night_hours
                            if is_additional_shift:
                                days_worked.append(
                                    f"{day} - {holiday_name} (+{day_hours:.0f}ч доп.)"
                                )
                            else:
                                days_worked.append(
                                    f"{day} - {holiday_name} (+{day_hours:.0f}ч)"
                                )
                        else:
                            night_hours += shift_night_hours
                            if is_additional_shift:
                                days_worked.append(
                                    f"{day} - Доп. смена (+{day_hours:.0f}ч)"
                                )
                    except (ValueError, Exception):
                        # Ignore date parsing errors or API failures
                        night_hours += shift_night_hours
                        if is_additional_shift:
                            days_worked.append(
                                f"{day} - Доп. смена (+{day_hours:.0f}ч)"
                            )

                    total_hours += day_hours
                    working_days += 1

        return (
            total_hours,
            night_hours,
            holiday_hours,
            night_holiday_hours,
            working_days,
            days_worked,
        )

    @classmethod
    async def calculate_salary(
            cls, user: Employee, premium_data, current_month: Optional[str] = None
    ) -> SalaryCalculationResult:
        """Calculate complete salary for a user"""
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5)))
        current_month_name = current_month or russian_months[now.month]

        # Get pay rate
        pay_rate = PayRateService.get_pay_rate(user.division, user.position)
        if pay_rate == 0.0:
            raise ValueError(
                f"No pay rate found for division '{user.division}' and position '{user.position}'"
            )

        # Get schedule data
        schedule_parser = ScheduleParser()
        try:
            schedule_data, additional_shifts_data = (
                schedule_parser.get_user_schedule_with_additional_shifts(
                    user.fullname, current_month_name, user.division
                )
            )
        except Exception as e:
            raise Exception(f"Произошла ошибка при расчете: {e}")

        # Process regular schedule
        (
            total_working_hours,
            night_hours,
            holiday_hours,
            night_holiday_hours,
            working_days,
            holiday_days_worked,
        ) = await cls._process_schedule_data(
            schedule_data, now, is_additional_shift=False
        )

        # Process additional shifts
        (
            additional_shift_hours,
            additional_shift_night_hours,
            additional_shift_holiday_hours,
            additional_shift_night_holiday_hours,
            _,
            additional_shift_days_worked,
        ) = await cls._process_schedule_data(
            additional_shifts_data, now, is_additional_shift=True
        )

        # Calculate regular hours (exclude night and holiday from total)
        regular_hours = (
                total_working_hours - holiday_hours - night_hours - night_holiday_hours
        )
        regular_additional_shift_hours = (
                additional_shift_hours
                - additional_shift_holiday_hours
                - additional_shift_night_hours
                - additional_shift_night_holiday_hours
        )

        # Calculate base salary
        base_salary = (
                (regular_hours * pay_rate)
                + (holiday_hours * pay_rate * PayRateService.get_holiday_multiplier())
                + (night_hours * pay_rate * PayRateService.get_night_multiplier())
                + (
                        night_holiday_hours
                        * pay_rate
                        * PayRateService.get_night_holiday_multiplier()
                )
        )

        # Calculate additional shifts salary
        additional_shift_rate = (
                pay_rate * PayRateService.get_additional_shift_multiplier()
        )
        additional_shift_holiday_rate = (
                additional_shift_rate * PayRateService.get_holiday_multiplier()
        )
        additional_shift_night_rate = (
                additional_shift_rate * PayRateService.get_night_multiplier()
        )
        additional_shift_night_holiday_rate = (
                additional_shift_rate * PayRateService.get_night_holiday_multiplier()
        )

        additional_shift_salary = (
                (regular_additional_shift_hours * additional_shift_rate)
                + (additional_shift_holiday_hours * additional_shift_holiday_rate)
                + (additional_shift_night_hours * additional_shift_night_rate)
                + (
                        additional_shift_night_holiday_hours
                        * additional_shift_night_holiday_rate
                )
        )

        # Calculate individual KPI premium amounts (based only on base salary)
        csi_premium_amount = base_salary * ((premium_data.csi_premium or 0) / 100)
        flr_premium_amount = base_salary * ((premium_data.flr_premium or 0) / 100)
        gok_premium_amount = base_salary * ((premium_data.gok_premium or 0) / 100)
        target_premium_amount = base_salary * ((premium_data.target_premium or 0) / 100)
        discipline_premium_amount = base_salary * (
                (premium_data.discipline_premium or 0) / 100
        )
        tests_premium_amount = base_salary * ((premium_data.tests_premium or 0) / 100)
        thanks_premium_amount = base_salary * ((premium_data.thanks_premium or 0) / 100)
        tutors_premium_amount = base_salary * ((premium_data.tutors_premium or 0) / 100)
        head_adjust_premium_amount = base_salary * (
                (premium_data.head_adjust_premium or 0) / 100
        )

        # Calculate total premium
        premium_multiplier = (premium_data.total_premium or 0) / 100
        premium_amount = base_salary * premium_multiplier
        total_salary = base_salary + premium_amount + additional_shift_salary

        return SalaryCalculationResult(
            user=user,
            current_month_name=current_month_name,
            current_year=now.year,
            pay_rate=pay_rate,
            working_days=working_days,
            total_working_hours=total_working_hours,
            regular_hours=regular_hours,
            night_hours=night_hours,
            holiday_hours=holiday_hours,
            night_holiday_hours=night_holiday_hours,
            holiday_days_worked=holiday_days_worked,
            additional_shift_hours=additional_shift_hours,
            additional_shift_holiday_hours=additional_shift_holiday_hours,
            additional_shift_night_hours=additional_shift_night_hours,
            additional_shift_night_holiday_hours=additional_shift_night_holiday_hours,
            additional_shift_days_worked=additional_shift_days_worked,
            base_salary=base_salary,
            additional_shift_salary=additional_shift_salary,
            additional_shift_rate=additional_shift_rate,
            additional_shift_holiday_rate=additional_shift_holiday_rate,
            additional_shift_night_rate=additional_shift_night_rate,
            additional_shift_night_holiday_rate=additional_shift_night_holiday_rate,
            csi_premium_amount=csi_premium_amount,
            flr_premium_amount=flr_premium_amount,
            gok_premium_amount=gok_premium_amount,
            target_premium_amount=target_premium_amount,
            discipline_premium_amount=discipline_premium_amount,
            tests_premium_amount=tests_premium_amount,
            thanks_premium_amount=thanks_premium_amount,
            tutors_premium_amount=tutors_premium_amount,
            head_adjust_premium_amount=head_adjust_premium_amount,
            premium_amount=premium_amount,
            total_salary=total_salary,
            calculation_time=now,
            premium_updated_at=getattr(premium_data, "updated_at", None),
        )
