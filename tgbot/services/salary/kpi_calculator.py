"""Калькулятор показателей и порогов премии."""

import datetime

from stp_database.models.Stats import HeadPremium, SpecPremium
from stp_database.models.STP import Employee

from tgbot.misc.helpers import strftime_date
from tgbot.services.salary import SalaryFormatter


class KPICalculator:
    """Сервиса для расчета показателей и выполнения порогов премии."""

    @staticmethod
    def calculate_csat_needed(division: str, current_csat, normative):
        """Расчет CSAT, необходимого для достижения уровней премии.

        Args:
            division: Направление сотрудника
            current_csat: Текущее значение CSAT
            normative: Норматив CSAT

        Returns:
            Строку с выполнением норматива CSAT
        """
        if normative == 0 or normative is None:
            return "—"

        current_csat = current_csat or 0

        # Вычисляем текущий процент выполнения норматива
        current_rate = (current_csat / normative * 100) if normative > 0 else 0

        results = []

        # Новые пороги для CSAT (одинаковые для всех направлений)
        csat_thresholds = [
            (110, 21.45, "≥ 110,0%"),
            (109, 21.26, "109,0% - 109,99%"),
            (108, 21.06, "108,0% - 108,99%"),
            (107, 20.87, "107,0% - 107,99%"),
            (106, 20.67, "106,0% - 106,99%"),
            (105, 20.48, "105,0% - 105,99%"),
            (104, 20.28, "104,0% - 104,99%"),
            (103, 20.09, "103,0% - 103,99%"),
            (102, 19.89, "102,0% - 102,99%"),
            (101, 19.70, "101,0% - 101,99%"),
            (100, 19.50, "100,0% - 100,99%"),
            (95, 17.55, "95,0% - 99,99%"),
            (90, 15.60, "90,0% - 94,99%"),
            (0, 0.00, "&lt; 90%"),
        ]

        for threshold, premium_percent, description in csat_thresholds:
            # Проверяем, попадает ли текущий процент в диапазон
            if threshold == 110:
                # Для верхнего порога проверяем >= 110
                is_in_range = current_rate >= threshold
            elif threshold == 0:
                # Для нижнего порога проверяем < 90
                is_in_range = current_rate < 90
            else:
                # Для промежуточных порогов: threshold <= current_rate < (threshold+1)
                is_in_range = threshold <= current_rate < (threshold + 1)

            if is_in_range:
                results.append(f"{premium_percent}%: ✅ ({description})")
            else:
                # Вычисляем значение CSAT для достижения этого диапазона
                needed_csat = (threshold / 100) * normative
                if threshold > 0 and current_csat < needed_csat:
                    difference = needed_csat - current_csat
                    results.append(
                        f"{premium_percent}%: {needed_csat:.2f} [+{difference:.2f}] ({description})"
                    )
                elif threshold == 0:
                    # Для нижнего порога не показываем разницу
                    results.append(f"{premium_percent}%: — ({description})")
                else:
                    results.append(f"{premium_percent}%: ✅ ({description})")

        return "\n".join(results)

    @staticmethod
    def calculate_flr_needed(
        division: str, current_flr, normative, is_head: bool = False
    ):
        """Расчет FLR, необходимого для достижения уровней премии.

        Args:
            division: Направление сотрудника
            current_flr: Текущее значение FLR
            normative: Норматив FLR
            is_head: Является ли сотрудник руководителем

        Returns:
            Строку с выполнением норматива FLR
        """
        if normative == 0 or normative is None:
            return "—"

        current_flr = current_flr or 0

        thresholds = []
        results = []

        if is_head:
            # Пороги для руководителей
            if division == "НЦК":
                thresholds = [
                    (102, 25, "≥ 102%"),
                    (101.4, 23, "≥ 101,40%"),
                    (100.7, 18, "≥ 100,70%"),
                    (100, 16, "≥ 100%"),
                    (96, 14, "≥ 96%"),
                    (0, 10, "&lt; 96%"),
                ]
            elif division in ["НТП1", "НТП2"]:
                thresholds = [
                    (104, 25, "≥ 104%"),
                    (102, 22, "≥ 102%"),
                    (101, 20, "≥ 101%"),
                    (100, 16, "≥ 100%"),
                    (98, 14, "≥ 98%"),
                    (0, 10, "&lt; 98%"),
                ]
        else:
            # Пороги для специалистов
            if division == "НЦК":
                thresholds = [
                    (103, 30, "≥ 103%"),
                    (102, 25, "≥ 102%"),
                    (101, 21, "≥ 101%"),
                    (100, 18, "≥ 100%"),
                    (95, 13, "≥ 95%"),
                    (0, 8, "&lt; 95%"),
                ]
            elif division == "НТП1":
                thresholds = [
                    (109, 30, "≥ 109%"),
                    (106, 25, "≥ 106%"),
                    (103, 21, "≥ 103%"),
                    (100, 18, "≥ 100%"),
                    (90, 13, "≥ 90%"),
                    (0, 8, "&lt; 90%"),
                ]
            elif division == "НТП2":
                thresholds = [
                    (107, 30, "≥ 107%"),
                    (104, 25, "≥ 104%"),
                    (102, 21, "≥ 102%"),
                    (100, 18, "≥ 100%"),
                    (97, 13, "≥ 97%"),
                    (0, 8, "&lt; 97%"),
                ]

        for threshold, premium_percent, description in thresholds:
            needed_flr = (threshold / 100) * normative

            if current_flr >= needed_flr:
                results.append(f"{premium_percent}%: ✅ ({description})")
            else:
                difference = needed_flr - current_flr
                results.append(
                    f"{premium_percent}%: {needed_flr:.2f} [+{difference:.2f}] ({description})"
                )

        return "\n".join(results)

    @staticmethod
    def calculate_gok_needed(
        division: str, current_gok, normative, is_head: bool = False
    ) -> str:
        """Расчет ГОК, необходимого для достижения уровней премии.

        Args:
            division: Направление сотрудника
            current_gok: Текущее значение ГОК
            normative: Норматив ГОК
            is_head: Является ли сотрудник руководителем

        Returns:
            Строку с выполнением норматива ГОК
        """
        if normative == 0 or normative is None:
            return "—"

        current_gok = current_gok or 0

        # Вычисляем текущий процент выполнения норматива
        current_rate = (current_gok / normative * 100) if normative > 0 else 0

        results = []

        # Новые пороги для ГОК (одинаковые для всех направлений и ролей)
        gok_thresholds = [
            (110, 21.45, "≥ 110,0%"),
            (109, 21.26, "109,0% - 109,99%"),
            (108, 21.06, "108,0% - 108,99%"),
            (107, 20.87, "107,0% - 107,99%"),
            (106, 20.67, "106,0% - 106,99%"),
            (105, 20.48, "105,0% - 105,99%"),
            (104, 20.28, "104,0% - 104,99%"),
            (103, 20.09, "103,0% - 103,99%"),
            (102, 19.89, "102,0% - 102,99%"),
            (101, 19.70, "101,0% - 101,99%"),
            (100, 19.50, "100,0% - 100,99%"),
            (95, 17.55, "95,0% - 99,99%"),
            (90, 15.60, "90,0% - 94,99%"),
            (0, 0.00, "&lt; 90%"),
        ]

        for threshold, premium_percent, description in gok_thresholds:
            # Проверяем, попадает ли текущий процент в диапазон
            if threshold == 110:
                # Для верхнего порога проверяем >= 110
                is_in_range = current_rate >= threshold
            elif threshold == 0:
                # Для нижнего порога проверяем < 90
                is_in_range = current_rate < 90
            else:
                # Для промежуточных порогов: threshold <= current_rate < (threshold+1)
                is_in_range = threshold <= current_rate < (threshold + 1)

            if is_in_range:
                results.append(f"{premium_percent}%: ✅ ({description})")
            else:
                # Вычисляем значение ГОК для достижения этого диапазона
                needed_gok = (threshold / 100) * normative
                if threshold > 0 and current_gok < needed_gok:
                    difference = needed_gok - current_gok
                    results.append(
                        f"{premium_percent}%: {needed_gok:.2f} [+{difference:.2f}] ({description})"
                    )
                elif threshold == 0:
                    # Для нижнего порога не показываем разницу
                    results.append(f"{premium_percent}%: — ({description})")
                else:
                    results.append(f"{premium_percent}%: ✅ ({description})")

        return "\n".join(results)

    @staticmethod
    def calculate_aht_needed(division: str, current_aht, normative):
        """Расчет AHT, необходимого для достижения уровней премии.

        Args:
            division: Направление сотрудника
            current_aht: Текущее значение AHT
            normative: Норматив AHT

        Returns:
            Строку с выполнением норматива AHT
        """
        if normative == 0 or normative is None:
            return "—"

        current_aht = current_aht or 0

        # Вычисляем текущий процент выполнения норматива
        # Для AHT: чем ниже значение, тем лучше, поэтому считаем наоборот
        current_rate = (normative / current_aht * 100) if current_aht > 0 else 0

        results = []

        # Пороги для AHT (одинаковые для всех направлений)
        # Для AHT норматив считается наоборот: чем ниже текущее значение, тем выше процент
        aht_thresholds = [
            (110, 28.60, "≥ 110,0%"),
            (109, 28.34, "109,0% - 109,99%"),
            (108, 28.08, "108,0% - 108,99%"),
            (107, 27.82, "107,0% - 107,99%"),
            (106, 27.56, "106,0% - 106,99%"),
            (105, 27.30, "105,0% - 105,99%"),
            (104, 27.04, "104,0% - 104,99%"),
            (103, 26.78, "103,0% - 103,99%"),
            (102, 26.52, "102,0% - 102,99%"),
            (101, 26.26, "101,0% - 101,99%"),
            (100, 26.00, "100,0% - 100,99%"),
            (95, 23.40, "95,0% - 99,99%"),
            (90, 20.80, "90,0% - 94,99%"),
            (0, 0.00, "&lt; 90%"),
        ]

        for threshold, premium_percent, description in aht_thresholds:
            # Проверяем, попадает ли текущий процент в диапазон
            if threshold == 110:
                # Для верхнего порога проверяем >= 110
                is_in_range = current_rate >= threshold
            elif threshold == 0:
                # Для нижнего порога проверяем < 90
                is_in_range = current_rate < 90
            else:
                # Для промежуточных порогов: threshold <= current_rate < (threshold+1)
                is_in_range = threshold <= current_rate < (threshold + 1)

            if is_in_range:
                results.append(f"{premium_percent}%: ✅ ({description})")
            else:
                # Вычисляем значение AHT для достижения этого диапазона
                # Для AHT считаем наоборот: нужно разделить норматив на процент
                needed_aht = (normative * 100) / threshold if threshold > 0 else 0
                if threshold > 0 and current_aht > needed_aht:
                    difference = current_aht - needed_aht
                    results.append(
                        f"{premium_percent}%: {needed_aht:.2f} [-{difference:.2f}] ({description})"
                    )
                elif threshold == 0:
                    # Для нижнего порога не показываем разницу
                    results.append(f"{premium_percent}%: — ({description})")
                else:
                    results.append(f"{premium_percent}%: ✅ ({description})")

        return "\n".join(results)

    @classmethod
    def format_requirements_message(
        cls, user: Employee, premium: SpecPremium | HeadPremium, is_head: bool = False
    ) -> str:
        """Форматирует сообщение с порогами премии за показатели.

        Args:
            user: Экземпляр пользователя с моделью Employee
            premium: Экземпляр премии сотрудника
            is_head: Является ли сотрудник руководителем

        Returns:
            Форматированную строку для отображения в боте
        """
        if is_head:
            # Для руководителей: FLR, GOK, AHT
            flr_calculation = cls.calculate_flr_needed(
                user.division, premium.flr, premium.flr_normative, is_head=is_head
            )
            gok_calculation = cls.calculate_gok_needed(
                user.division, premium.gok, premium.gok_normative, is_head=is_head
            )
            aht_calculation = cls.calculate_aht_needed(
                user.division, premium.aht, premium.aht_normative
            )

            message_text = f"""🧮 <b>Калькулятор KPI</b>

🔧 <b>FLR</b>
<blockquote>Текущий: {SalaryFormatter.format_value(premium.flr)} ({SalaryFormatter.format_percentage(premium.flr_normative_rate)})
План: {SalaryFormatter.format_value(premium.flr_normative)}

<b>Для премии:</b>
{flr_calculation}</blockquote>

⚖️ <b>ГОК</b>
<blockquote>Текущий: {SalaryFormatter.format_value(round(premium.gok))} ({SalaryFormatter.format_percentage(premium.gok_normative_rate)})
План: {SalaryFormatter.format_value(round(premium.gok_normative))}

<b>Для премии:</b>
{gok_calculation}</blockquote>

⏱️ <b>AHT</b>
<blockquote>Текущий: {SalaryFormatter.format_value(premium.aht)} ({SalaryFormatter.format_percentage(premium.aht_normative_rate)})
План: {SalaryFormatter.format_value(premium.aht_normative)}

<b>Для премии:</b>
{aht_calculation}</blockquote>

<i>Данные из <b><a href='okc.ertelecom.ru/yii/ure/report/index'>URE</a></b> на <code>{premium.updated_at.strftime(strftime_date)}</code>
Меню обновлено в <code>{datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5))).strftime(strftime_date)}</code></i>"""
        else:
            # Для специалистов: CSAT, GOK, AHT
            csat_calculation = cls.calculate_csat_needed(
                user.division, premium.csat, premium.csat_normative
            )
            gok_calculation = cls.calculate_gok_needed(
                user.division, premium.gok, premium.gok_normative, is_head=is_head
            )
            aht_calculation = cls.calculate_aht_needed(
                user.division, premium.aht, premium.aht_normative
            )

            message_text = f"""🧮 <b>Калькулятор KPI</b>

🌟 <b>CSAT</b>
<blockquote>Текущий: {SalaryFormatter.format_value(premium.csat)} ({SalaryFormatter.format_percentage(premium.csat_normative_rate)})
План: {SalaryFormatter.format_value(premium.csat_normative)}

<b>Для премии:</b>
{csat_calculation}</blockquote>

⚖️ <b>ГОК</b>
<blockquote>Текущий: {SalaryFormatter.format_value(round(premium.gok))} ({SalaryFormatter.format_percentage(premium.gok_normative_rate)})
План: {SalaryFormatter.format_value(round(premium.gok_normative))}

<b>Для премии:</b>
{gok_calculation}</blockquote>

⏱️ <b>AHT</b>
<blockquote>Текущий: {SalaryFormatter.format_value(premium.aht)} ({SalaryFormatter.format_percentage(premium.aht_normative_rate)})
План: {SalaryFormatter.format_value(premium.aht_normative)}

<b>Для премии:</b>
{aht_calculation}</blockquote>

<i>Данные из <b><a href='okc.ertelecom.ru/yii/ure/report/index'>URE</a></b> на <code>{premium.updated_at.strftime(strftime_date) if premium.updated_at else "—"}</code>
Меню обновлено в <code>{datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5))).strftime(strftime_date)}</code></i>"""
        return message_text
