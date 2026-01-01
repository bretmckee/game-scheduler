# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


"""Tests for data_access module structure.

Verifies that the guild-scoped query wrapper module structure is correctly set up
and can be imported. This is the foundation test for Task 1.1.
"""


def test_data_access_module_imports():
    """Verify data_access module and submodules can be imported."""
    import shared.data_access
    import shared.data_access.guild_queries

    assert hasattr(shared.data_access, "guild_queries")
    assert shared.data_access.guild_queries.__doc__ is not None


def test_guild_queries_module_structure():
    """Verify guild_queries module has correct structure and documentation."""
    from shared.data_access import guild_queries

    assert guild_queries.__name__ == "shared.data_access.guild_queries"
    assert "guild isolation" in guild_queries.__doc__.lower()
    assert "required guild_id" in guild_queries.__doc__.lower()
