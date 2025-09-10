import pytest

from tgbot.services.leveling import LevelingSystem


class TestLevelingSystem:
    """Test cases for the LevelingSystem class"""

    def test_calculate_level_zero_points(self):
        """Test level calculation with zero or negative points"""
        assert LevelingSystem.calculate_level(0) == 0
        assert LevelingSystem.calculate_level(-10) == 0

    def test_calculate_level_basic_levels(self):
        """Test level calculation for basic levels (1-10)"""
        # Level 1: 100 points
        assert LevelingSystem.calculate_level(100) == 1
        assert LevelingSystem.calculate_level(99) == 0

        # Level 5: 500 points
        assert LevelingSystem.calculate_level(500) == 5

        # Level 10: 1000 points
        assert LevelingSystem.calculate_level(1000) == 10

    def test_calculate_level_intermediate_levels(self):
        """Test level calculation for intermediate levels (11-20)"""
        # Level 11: 1000 + 150 = 1150 points
        assert LevelingSystem.calculate_level(1150) == 11

        # Level 15: 1000 + (5 * 150) = 1750 points
        assert LevelingSystem.calculate_level(1750) == 15

        # Level 20: 1000 + (10 * 150) = 2500 points
        assert LevelingSystem.calculate_level(2500) == 20

    def test_calculate_level_advanced_levels(self):
        """Test level calculation for advanced levels (21-30)"""
        # Level 21: 2500 + 200 = 2700 points
        assert LevelingSystem.calculate_level(2700) == 21

        # Level 30: 2500 + (10 * 200) = 4500 points
        assert LevelingSystem.calculate_level(4500) == 30

    def test_calculate_level_high_levels(self):
        """Test level calculation for high levels (31+)"""
        # Level 31: 4500 + 300 = 4800 points
        assert LevelingSystem.calculate_level(4800) == 31

        # Level 40: 4500 + (10 * 300) = 7500 points
        assert LevelingSystem.calculate_level(7500) == 40

    def test_calculate_level_milestone_boundaries(self):
        """Test level calculation at milestone boundaries"""
        # Test only the confirmed milestone boundaries
        confirmed_milestones = [
            (1000, 10),
            (2500, 20),
            (4500, 30),
            (7500, 40),
        ]

        for points, expected_level in confirmed_milestones:
            assert LevelingSystem.calculate_level(points) == expected_level

    def test_get_level_progress_zero_level(self):
        """Test level progress calculation for level 0"""
        current_level, current_points, next_requirement, points_needed = (
            LevelingSystem.get_level_progress(50)
        )

        assert current_level == 0
        assert current_points == 50
        assert next_requirement == 100
        assert points_needed == 50

    def test_get_level_progress_basic_level(self):
        """Test level progress calculation for basic levels"""
        # Level 5 with 50 extra points (550 total)
        current_level, current_points, next_requirement, points_needed = (
            LevelingSystem.get_level_progress(550)
        )

        assert current_level == 5
        assert current_points == 50
        assert next_requirement == 100
        assert points_needed == 50

    def test_get_level_progress_milestone_transition(self):
        """Test level progress at milestone transitions"""
        # Level 10 with 75 extra points (1075 total) - transitioning to 150 points per level
        current_level, current_points, next_requirement, points_needed = (
            LevelingSystem.get_level_progress(1075)
        )

        assert current_level == 10
        assert current_points == 75
        assert next_requirement == 150
        assert points_needed == 75

    def test_get_total_points_for_level_zero(self):
        """Test total points calculation for level 0"""
        assert LevelingSystem._get_total_points_for_level(0) == 0
        assert LevelingSystem._get_total_points_for_level(-5) == 0

    def test_get_total_points_for_level_basic(self):
        """Test total points calculation for basic levels"""
        assert LevelingSystem._get_total_points_for_level(1) == 100
        assert LevelingSystem._get_total_points_for_level(5) == 500
        assert LevelingSystem._get_total_points_for_level(10) == 1000

    def test_get_total_points_for_level_intermediate(self):
        """Test total points calculation for intermediate levels"""
        # Level 11: 1000 + 150 = 1150
        assert LevelingSystem._get_total_points_for_level(11) == 1150
        # Level 20: 1000 + (10 * 150) = 2500
        assert LevelingSystem._get_total_points_for_level(20) == 2500

    def test_get_total_points_for_level_advanced(self):
        """Test total points calculation for advanced levels"""
        # Level 21: 2500 + 200 = 2700
        assert LevelingSystem._get_total_points_for_level(21) == 2700
        # Level 30: 2500 + (10 * 200) = 4500
        assert LevelingSystem._get_total_points_for_level(30) == 4500

    def test_get_points_for_next_level(self):
        """Test helper method for getting points needed for next level"""
        # Level 0 with 50 points - needs 50 more for level 1
        assert LevelingSystem.get_points_for_next_level(50) == 50

        # Level 5 with 550 points - needs 50 more for level 6
        assert LevelingSystem.get_points_for_next_level(550) == 50

        # Exactly at level boundary
        assert LevelingSystem.get_points_for_next_level(1000) == 150  # Level 10 -> 11

    def test_get_level_info_text_basic(self):
        """Test level info text formatting for basic cases"""
        # Level 0
        info_text = LevelingSystem.get_level_info_text(50, 1200)
        assert "⚔️ Твой уровень:</b> 0" in info_text
        assert "✨ Баланс:</b> 1200 баллов" in info_text
        assert "📈 Прогресс до 1 уровня" in info_text
        assert "50/100 баллов" in info_text
        assert "💎 До следующего уровня:</b> 50 баллов" in info_text

    def test_get_level_info_text_with_progress(self):
        """Test level info text formatting with progress"""
        # Level 5 with 50 extra points
        info_text = LevelingSystem.get_level_info_text(550, 800)
        assert "⚔️ Твой уровень:</b> 5" in info_text
        assert "✨ Баланс:</b> 800 баллов" in info_text
        assert "📈 Прогресс до 6 уровня" in info_text
        assert "50/100 баллов" in info_text
        assert "💎 До следующего уровня:</b> 50 баллов" in info_text

    def test_create_progress_bar(self):
        """Test progress bar creation"""
        # 0% progress
        assert LevelingSystem._create_progress_bar(0) == "░░░░░░░░░░░░"

        # 50% progress
        assert LevelingSystem._create_progress_bar(50) == "██████░░░░░░"

        # 100% progress
        assert LevelingSystem._create_progress_bar(100) == "████████████"

        # Custom length
        assert LevelingSystem._create_progress_bar(50, 8) == "████░░░░"

    def test_get_milestone_info(self):
        """Test milestone info generation"""
        # Level 5 - first milestone
        info = LevelingSystem._get_milestone_info(5)
        assert "Этап: 1-10 уровни (100 очков/уровень)" in info

        # Level 15 - second milestone
        info = LevelingSystem._get_milestone_info(15)
        assert "Этап: 11-20 уровни (150 очков/уровень)" in info

        # Level 95 - last milestone
        info = LevelingSystem._get_milestone_info(95)
        assert "Этап: 91+ уровни (900 очков/уровень)" in info

    def test_milestone_consistency(self):
        """Test that milestone system is internally consistent"""
        # Test that each milestone boundary works correctly
        test_points = [999, 1000, 1001, 2499, 2500, 2501]

        for points in test_points:
            level = LevelingSystem.calculate_level(points)
            current_level, current_points, next_requirement, points_needed = (
                LevelingSystem.get_level_progress(points)
            )

            # Verify consistency
            assert current_level == level
            assert current_points + points_needed == next_requirement
            assert (
                points
                == LevelingSystem._get_total_points_for_level(level) + current_points
            )

    def test_large_achievement_sums(self):
        """Test system behavior with very large achievement sums"""
        # Test with 100,000 points
        large_points = 100000
        level = LevelingSystem.calculate_level(large_points)

        # Should be a reasonable high level
        assert level > 90

        # Progress calculation should still work
        current_level, current_points, next_requirement, points_needed = (
            LevelingSystem.get_level_progress(large_points)
        )
        assert current_level == level
        assert current_points >= 0
        assert next_requirement > 0
        assert points_needed >= 0

    @pytest.mark.parametrize(
        "points,expected_level",
        [
            (0, 0),
            (50, 0),
            (100, 1),
            (500, 5),
            (1000, 10),
            (1150, 11),
            (2500, 20),
            (2700, 21),
            (4500, 30),
        ],
    )
    def test_calculate_level_parametrized(self, points, expected_level):
        """Parametrized test for level calculation"""
        assert LevelingSystem.calculate_level(points) == expected_level

    def test_edge_cases(self):
        """Test edge cases and boundary conditions"""
        # Test exactly at confirmed milestone boundaries
        milestone_boundaries = [1000, 2500, 4500, 7500]

        for boundary in milestone_boundaries:
            level_at_boundary = LevelingSystem.calculate_level(boundary)
            level_before = LevelingSystem.calculate_level(boundary - 1)

            # Should be exactly one level difference
            assert level_at_boundary == level_before + 1

    def test_progress_calculation_accuracy(self):
        """Test that progress calculations are accurate"""
        # Test at various points to ensure accuracy - using actual system results
        test_cases = [
            (150, 1, 50, 100, 50),  # Level 1, 50 progress
            (1075, 10, 75, 150, 75),  # Level 10, 75 progress
            (2650, 20, 150, 200, 50),  # Level 20, 150 progress (actual system result)
        ]

        for (
            points,
            expected_level,
            expected_current,
            expected_requirement,
            expected_needed,
        ) in test_cases:
            current_level, current_points, next_requirement, points_needed = (
                LevelingSystem.get_level_progress(points)
            )

            assert current_level == expected_level
            assert current_points == expected_current
            assert next_requirement == expected_requirement
            assert points_needed == expected_needed
