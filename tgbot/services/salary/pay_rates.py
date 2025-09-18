class PayRateService:
    @staticmethod
    def get_pay_rate(division: str, position: str) -> float:
        """Get hourly pay rate based on division and position"""
        pay_rate = 0.0

        match division:
            case "НЦК":
                match position:
                    case "Специалист":
                        pay_rate = 156.7
                    case "Ведущий специалист":
                        pay_rate = 164.2
                    case "Эксперт":
                        pay_rate = 195.9
                    case "Руководитель группы":
                        pay_rate = 225.3
            case "НТП1":
                match position:
                    case "Специалист первой линии":
                        pay_rate = 143.6
                    case "Руководитель группы":
                        pay_rate = 256.1
            case "НТП2":
                match position:
                    case "Специалист второй линии":
                        pay_rate = 166
                    case "Ведущий специалист второй линии":
                        pay_rate = 181
                    case "Эксперт второй линии":
                        pay_rate = 195.9
                    case "Руководитель группы":
                        pay_rate = 256.1

        return pay_rate

    @staticmethod
    def get_additional_shift_multiplier() -> float:
        """Get multiplier for additional shifts (2.63)"""
        return 2.63

    @staticmethod
    def get_holiday_multiplier() -> float:
        """Get multiplier for holiday hours (2.0)"""
        return 2.0

    @staticmethod
    def get_night_multiplier() -> float:
        """Get multiplier for night hours (1.2)"""
        return 1.2

    @staticmethod
    def get_night_holiday_multiplier() -> float:
        """Get multiplier for night holiday hours (2.4)"""
        return 2.4
