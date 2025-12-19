from ...misc.helpers import strftime_date
from .salary_calculator import SalaryCalculationResult


class SalaryFormatter:
    """Утилита для форматирования результатов расчета заработной платы и показателей."""

    @staticmethod
    def format_value(value, suffix=""):
        """Форматирует численное значение с суффиксом.

        Args:
            value: Неформатированное значение
            suffix: Суффикс для подстановки после значения

        Returns:
            Форматированное значение показателя, или '—' если None
        """
        if value is None:
            return "—"

        if isinstance(value, (int, float)):
            return f"{value:g}{suffix}"

        return f"{value}{suffix}"

    @staticmethod
    def format_percentage(value):
        """Форматирует процентное значение.

        Args:
            value:

        Returns:
            Форматированное значение показателя, или '—' если None
        """
        return f"{value}%" if value is not None else "—"

    @classmethod
    def format_salary_message(
        cls, result: SalaryCalculationResult, premium_data
    ) -> str:
        """Форматирует сообщение с расчетом зарплаты.

        Args:
            result: Результат расчета частей зарплаты
            premium_data: Показатели из премиума

        Returns:
            Форматированное сообщение
        """
        # Форматирование блока рабочих часов
        hours_details = []
        if result.regular_hours > 0:
            hours_details.append(
                f"Обычные часы: {result.regular_hours:g}ч × {result.pay_rate:g} ₽ = {result.regular_hours * result.pay_rate:g} ₽"
            )
        if result.night_hours > 0:
            hours_details.append(
                f"Ночные часы: {result.night_hours:g}ч × {result.pay_rate * 1.2:g} ₽ = {result.night_hours * result.pay_rate * 1.2:g} ₽"
            )
        if result.holiday_hours > 0:
            hours_details.append(
                f"Праздничные часы: {result.holiday_hours:g}ч × {result.pay_rate * 2:g} ₽ = {result.holiday_hours * result.pay_rate * 2:g} ₽"
            )
        if result.night_holiday_hours > 0:
            hours_details.append(
                f"Ночные праздничные часы: {result.night_holiday_hours:g}ч × {result.pay_rate * 2.4:g} ₽ = {result.night_holiday_hours * result.pay_rate * 2.4:g} ₽"
            )

        # Форматирование блока дополнительных смен
        additional_shifts_details = []
        if result.additional_shift_hours > 0:
            additional_shifts_details.append(
                f"Доп. смены: {result.additional_shift_hours:g}ч × {result.additional_shift_rate:g} ₽ = {result.additional_shift_salary:g} ₽"
            )

        message_text = f"""💰 <b>Зарплата</b>

⏰ <b>Рабочие часы:</b>
<blockquote>Рабочих дней: {result.working_days}
Всего часов: {result.total_working_hours:g}{
            f'''

🎉 Праздничные дни (x2): {result.holiday_hours:g}ч
{chr(10).join(result.holiday_days_worked)}'''
            if result.holiday_days_worked
            else ""
        }{
            f'''

⭐ Доп. смены: {result.additional_shift_hours:g}ч
{chr(10).join(result.additional_shift_days_worked)}'''
            if result.additional_shift_days_worked
            else ""
        }</blockquote>

💵 <b>Оклад:</b>
<blockquote>Ставка в час: {cls.format_value(result.pay_rate, " ₽")}

{chr(10).join(hours_details)}

Сумма оклада: {cls.format_value(result.base_salary, " ₽")}</blockquote>{
            f'''

⭐ <b>Доп. смены:</b>
<blockquote>{chr(10).join(additional_shifts_details)}

Сумма доп. смен: {cls.format_value(result.additional_shift_salary, " ₽")}</blockquote>'''
            if result.additional_shift_salary > 0
            else ""
        }

🎁 <b>Премия:</b>
<blockquote expandable>Общий процент премии: {
            cls.format_percentage(premium_data.total_premium)
        }
Общая сумма премии: {cls.format_value(result.premium_amount, " ₽")}
Стоимость 1% премии: ~{
            cls.format_value(result.premium_amount / premium_data.total_premium, " ₽")
            if premium_data.total_premium and premium_data.total_premium > 0
            else "0 ₽"
        }

🌟 Показатели:"""

        # Определяем тип премиум данных по роли пользователя
        is_head_premium = result.user.role == 2

        if is_head_premium:
            # Для руководителей - только FLR, GOK, цель и корректировка руководителя
            message_text += f"""
FLR: {cls.format_percentage(premium_data.flr_premium)} = {
                cls.format_value(result.flr_premium_amount, " ₽")
            }
ГОК: {cls.format_percentage(premium_data.gok_premium)} = {
                cls.format_value(result.gok_premium_amount, " ₽")
            }
Цель: {cls.format_percentage(premium_data.target_premium)} = {
                cls.format_value(result.target_premium_amount, " ₽")
            }

💼 Дополнительно:
Корректировка руководителя: {
                cls.format_percentage(premium_data.head_adjust_premium)
            } = {cls.format_value(result.head_adjust_premium_amount, " ₽")}"""
        else:
            # Для специалистов - все показатели
            message_text += f"""
Оценка: {cls.format_percentage(premium_data.csi_premium)} = {
                cls.format_value(result.csi_premium_amount, " ₽")
            }
FLR: {cls.format_percentage(premium_data.flr_premium)} = {
                cls.format_value(result.flr_premium_amount, " ₽")
            }
ГОК: {cls.format_percentage(premium_data.gok_premium)} = {
                cls.format_value(result.gok_premium_amount, " ₽")
            }
Цель: {cls.format_percentage(premium_data.target_premium)} = {
                cls.format_value(result.target_premium_amount, " ₽")
            }

💼 Дополнительно:
Дисциплина: {cls.format_percentage(premium_data.discipline_premium)} = {
                cls.format_value(result.discipline_premium_amount, " ₽")
            }
Тестирование: {cls.format_percentage(premium_data.tests_premium)} = {
                cls.format_value(result.tests_premium_amount, " ₽")
            }
Благодарности: {cls.format_percentage(premium_data.thanks_premium)} = {
                cls.format_value(result.thanks_premium_amount, " ₽")
            }
Наставничество: {cls.format_percentage(premium_data.tutors_premium)} = {
                cls.format_value(result.tutors_premium_amount, " ₽")
            }
Ручная правка: {cls.format_percentage(premium_data.head_adjust_premium)} = {
                cls.format_value(result.head_adjust_premium_amount, " ₽")
            }"""

        message_text += f"""</blockquote>

💰 <b>Итого к выплате:</b>
<blockquote>Полная зарплата: ~<b>{cls.format_value(result.total_salary, " ₽")}</b>

🏦 Аванс (1-15 числа): ~<b>{cls.format_value(result.advance_payment, " ₽")}</b>
<blockquote>Часы первой половины: {cls.format_value(result.first_half_hours, "ч")}
<i>(включая ночные/праздничные доплаты)</i></blockquote>

💵 Основная часть: ~<b>{cls.format_value(result.main_payment, " ₽")}</b>
<blockquote><i>(вторая половина + премии + доп. смены)</i></blockquote></blockquote>

<blockquote expandable>⚠️ <b>Важное</b>

Расчет представляет <b>примерную</b> сумму после вычета НДФЛ
Районный коэффициент <b>не участвует в расчете</b>, т.к. примерно покрывает НДФЛ

🧪 <b>Формулы</b>
Обычные часы: часы × ставка
Праздничные часы: часы × ставка × 2
Ночные часы: часы × ставка × 1.2
Ночные праздничные часы: часы × ставка × 2.4
Доп. смены: часы × (ставка × 2 × (1 + премия%))

Ночными часами считается локальное время 22:00 - 6:00
Праздничные дни считаются по производственному <a href='https://www.consultant.ru/law/ref/calendar/proizvodstvennye/'>календарю</a></blockquote>

<i>Данные из <b><a href='https://okc.ertelecom.ru/yii/ure/report/index'>URE</a></b> на <code>{result.premium_updated_at.strftime(strftime_date)}</code>
Меню обновлено в <code>{result.calculation_time.strftime(strftime_date)}</code></i>"""

        return message_text
