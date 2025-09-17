from typing import Optional


class KPICalculator:
    """Service for KPI calculations and premium thresholds"""

    @staticmethod
    def calculate_csi_needed(division: str, current_csi, normative):
        """Расчет оценки, необходимой для достижения уровней премии"""
        if normative == 0 or normative is None:
            return "—"

        current_csi = current_csi or 0

        results = []

        if division == "НЦК":
            thresholds = [
                (101, 20, "≥ 101%"),
                (100.5, 15, "≥ 100,5%"),
                (100, 10, "≥ 100%"),
                (98, 5, "≥ 98%"),
                (0, 0, "&lt; 98%"),
            ]
        elif division == "НТП1":
            thresholds = [
                (101, 20, "≥ 101%"),
                (100.5, 15, "≥ 100,5%"),
                (100, 10, "≥ 100%"),
                (98, 5, "≥ 98%"),
                (0, 0, "&lt; 98%"),
            ]
        else:
            thresholds = [
                (100.8, 20, "≥ 100.8%"),
                (100.4, 15, "≥ 100.4%"),
                (100, 10, "≥ 100%"),
                (98, 5, "≥ 98%"),
                (0, 0, "&lt; 98%"),
            ]

        for threshold, premium_percent, description in thresholds:
            needed_csi = (threshold / 100) * normative

            if current_csi >= needed_csi:
                results.append(f"{premium_percent}%: ✅ ({description})")
            else:
                difference = needed_csi - current_csi
                results.append(
                    f"{premium_percent}%: {needed_csi:.3f} [+{difference:.3f}] ({description})"
                )

        return "\n".join(results)

    @staticmethod
    def calculate_flr_needed(division: str, current_flr, normative):
        """Расчет FLR, необходимой для достижения уровней премии"""
        if normative == 0 or normative is None:
            return "—"

        current_flr = current_flr or 0

        results = []

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
        else:
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
    def calculate_gok_needed(division: str, current_gok, normative):
        """Расчет ГОК, необходимой для достижения уровней премии"""
        if normative == 0 or normative is None:
            return "—"

        current_gok = current_gok or 0

        results = []

        if division == "НЦК":
            thresholds = [
                (100, 17, "≥ 100%"),
                (95, 15, "≥ 95%"),
                (90, 12, "≥ 90%"),
                (85, 9, "≥ 85%"),
                (80, 5, "≥ 80%"),
                (0, 0, "&lt; 80%"),
            ]
        elif division == "НТП1":
            thresholds = [
                (100, 17, "≥ 100%"),
                (95, 15, "≥ 95%"),
                (90, 12, "≥ 90%"),
                (85, 9, "≥ 85%"),
                (80, 5, "≥ 80%"),
                (0, 0, "&lt; 80%"),
            ]
        else:
            thresholds = [
                (100, 17, "≥ 100%"),
                (95, 15, "≥ 95%"),
                (90, 12, "≥ 90%"),
                (84, 9, "≥ 84%"),
                (70, 5, "≥ 70%"),
                (0, 0, "&lt; 70%"),
            ]

        for threshold, premium_percent, description in thresholds:
            needed_gok = (threshold / 100) * normative

            if current_gok >= needed_gok:
                results.append(f"{premium_percent}%: ✅ ({description})")
            else:
                difference = needed_gok - current_gok
                results.append(
                    f"{premium_percent}%: {needed_gok:.3f} [+{difference:.3f}] ({description})"
                )

        return "\n".join(results)

    @staticmethod
    def calculate_target_needed(
        current_target,
        target_goal_first,
        target_goal_second,
        target_type: Optional[str] = None,
    ):
        """Расчет цели, необходимой для достижения уровней премии"""
        if target_goal_first is None and target_goal_second is None:
            return "—"

        current_target = current_target or 0

        # Определяем, является ли цель продажами (чем выше, тем лучше) или цель - AHT (чем ниже, тем лучше)
        is_sales_target = target_type and "Продажа оборудования" in target_type
        is_aht_target = target_type and "AHT" in target_type

        results = []

        # Все подразделения имеют одинаковые целевые пороги премии
        if target_goal_second and target_goal_second > 0:
            # Когда есть вторая цель, используем ее как основной план
            normative = target_goal_second

            if is_aht_target:
                # Для AHT, чем ниже, тем лучше — процент рассчитывается как (план / текущий * 100)
                target_rate = (
                    (normative / current_target * 100) if current_target > 0 else 0
                )
            elif is_sales_target:
                # Для продаж, чем выше, тем лучше — процент рассчитывается как (текущее / план * 100)
                target_rate = (current_target / normative * 100) if normative > 0 else 0
            else:
                # Поведение по умолчанию (чем выше, тем лучше) — процент рассчитывается как (текущее / план * 100)
                target_rate = (current_target / normative * 100) if normative > 0 else 0

            if target_rate > 100.01:
                results.append("28%: ✅ (≥ 100,01% - план 2 и более)")
            else:
                if is_aht_target:
                    # Для AHT нужно быть ниже плана
                    needed_for_28 = normative / (100.01 / 100)
                    difference = current_target - needed_for_28
                    results.append(
                        f"28%: {needed_for_28:.2f} [-{difference:.2f}] (≥ 100,01% - план 2 и более)"
                    )
                else:
                    # Для продаж нужно превысить план
                    needed_for_28 = (100.01 / 100) * normative
                    difference = needed_for_28 - current_target
                    results.append(
                        f"28%: {needed_for_28:.2f} [+{difference:.2f}] (≥ 100,01% - план 2 и более)"
                    )

            if target_rate >= 100.00:
                results.append("18%: ✅ (≥ 100,00% - план 1 и менее плана 2)")
            else:
                if is_aht_target:
                    needed_for_18 = normative / (100.00 / 100)
                    difference = current_target - needed_for_18
                    results.append(
                        f"18%: {needed_for_18:.2f} [-{difference:.2f}] (= 100,00% - план 1 и менее плана 2)"
                    )
                else:
                    needed_for_18 = (100.00 / 100) * normative
                    difference = needed_for_18 - current_target
                    results.append(
                        f"18%: {needed_for_18:.2f} [+{difference:.2f}] (= 100,00% - план 1 и менее плана 2)"
                    )

            if target_rate < 99.99:
                results.append("0%: — (&lt; 99,99% - менее плана 1)")
            else:
                results.append("0%: ✅ (&lt; 99,99% - менее плана 1)")

        elif target_goal_first and target_goal_first > 0:
            # Когда есть только первая цель, используем ее как план
            normative = target_goal_first

            if is_aht_target:
                target_rate = (
                    (normative / current_target * 100) if current_target > 0 else 0
                )
            elif is_sales_target:
                target_rate = (current_target / normative * 100) if normative > 0 else 0
            else:
                target_rate = (current_target / normative * 100) if normative > 0 else 0

            if target_rate > 100.01:
                results.append("28%: ✅ (≥ 100,01% - план 2 и более)")
            else:
                if is_aht_target:
                    needed_for_28 = normative / (100.01 / 100)
                    difference = current_target - needed_for_28
                    results.append(
                        f"28%: {needed_for_28:.2f} [-{difference:.2f}] (≥ 100,01% - план 2 и более)"
                    )
                else:
                    needed_for_28 = (100.01 / 100) * normative
                    difference = needed_for_28 - current_target
                    results.append(
                        f"28%: {needed_for_28:.2f} [+{difference:.2f}] (≥ 100,01% - план 2 и более)"
                    )

            if target_rate >= 100.00:
                results.append("18%: ✅ (≥ 100,00% - план 1 и менее плана 2)")
            else:
                if is_aht_target:
                    needed_for_18 = normative / (100.00 / 100)
                    difference = current_target - needed_for_18
                    results.append(
                        f"18%: {needed_for_18:.2f} [-{difference:.2f}] (≥ 100,00% - план 1 и менее плана 2)"
                    )
                else:
                    needed_for_18 = (100.00 / 100) * normative
                    difference = needed_for_18 - current_target
                    results.append(
                        f"18%: {needed_for_18:.2f} [+{difference:.2f}] (≥ 100,00% - план 1 и менее плана 2)"
                    )

            if target_rate < 99.99:
                results.append("0%: — (&lt; 99,99% - менее плана 1)")
            else:
                results.append("0%: ✅ (&lt; 99,99% - менее плана 1)")

        return "\n".join(results)
