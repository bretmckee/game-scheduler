# Copyright 2026 Bret McKee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


"""Unit tests for GameService.clone_game and _apply_deadline_carryover.

clone_game now delegates its entire mechanical pipeline (template loading,
host resolution, free-text/participant resolution, roster creation, and
publish) to create_game. These tests therefore mock self.create_game itself
and verify only clone_game's own orchestration: the permission gate, the
GameCreateRequest payload constructed from clone_data/source_game, the
default_host_user_id/host_user_id split, and the additive image-carryover
step. Full-pipeline behaviors (template loading, real mention resolution,
real permission role checks) are covered by
tests/integration/test_clone_game_endpoint.py instead.

Phase 5 adds one more orchestration behavior to verify: clone_game computes
carryover-eligible groups from the source game's own confirmed/overflow
partition, filtered down to the discord_ids actually present in the
delegated create_game() call's returned roster, and passes those groups to
the real (unmocked) _apply_deadline_carryover. Those tests patch only
get_game/can_manage_game/create_game -- same as the rest of this file -- and
assert on the ParticipantActionSchedule/NotificationSchedule rows added to
self.db, exactly like _apply_deadline_carryover's own direct-invocation
tests below.
"""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.api.schemas.clone_game import CarryoverOption, CloneGameRequest
from services.api.services import participant_resolver as resolver_module
from services.api.services.games import GameService
from shared.models import game as game_model
from shared.models import participant as participant_model
from shared.models.notification_schedule import NotificationSchedule
from shared.models.participant_action_schedule import ParticipantActionSchedule
from shared.models.signup_method import SignupMethod
from shared.schemas import auth as auth_schemas
from shared.schemas import game as game_schemas

SCHEDULED_AT = datetime.datetime(2026, 9, 1, 18, 0, 0, tzinfo=datetime.UTC)
CLONE_AT = datetime.datetime(2026, 10, 1, 18, 0, 0, tzinfo=datetime.UTC)
DEADLINE = datetime.datetime(2027, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)
CURRENT_USER_DB_ID = "current-user-db-uuid"


@pytest.fixture
def source_game():
    """Source game with two participants (one player, one waitlist)."""
    game = MagicMock(spec=game_model.GameSession)
    game.id = "source-game-uuid"
    game.title = "Original Game"
    game.description = "A great game"
    game.signup_instructions = "Join here"
    game.scheduled_at = SCHEDULED_AT
    game.where = "Discord"
    game.max_players = 1
    game.template_id = "template-uuid"
    game.guild_id = "guild-db-uuid"
    game.channel_id = "channel-db-uuid"
    game.host_id = "host-db-uuid"
    game.reminder_minutes = [30, 10]
    game.notify_role_ids = ["role-1"]
    game.allowed_player_role_ids = None
    game.expected_duration_minutes = 120
    game.status = game_model.GameStatus.SCHEDULED.value
    game.signup_method = SignupMethod.SELF_SIGNUP
    game.thumbnail_id = None
    game.banner_image_id = None
    game.message_id = "discord-message-id-999"
    game.remind_host_rewards = True
    game.reminders_as_dms = False
    game.recur_rule = None

    game.host = MagicMock()
    game.host.discord_id = "host-discord-id"
    game.guild = MagicMock()
    game.guild.guild_id = "guild-discord-id"
    game.channel = MagicMock()

    player = MagicMock(spec=participant_model.GameParticipant)
    player.user_id = "user1-uuid"
    player.display_name = None
    player.position_type = participant_model.ParticipantType.HOST_ADDED
    player.position = 1
    player.user = MagicMock()
    player.user.discord_id = "player1-discord"

    waitlisted = MagicMock(spec=participant_model.GameParticipant)
    waitlisted.user_id = "user2-uuid"
    waitlisted.display_name = None
    waitlisted.position_type = participant_model.ParticipantType.SELF_ADDED
    waitlisted.position = 2
    waitlisted.user = MagicMock()
    waitlisted.user.discord_id = "player2-discord"

    game.participants = [player, waitlisted]
    return game


@pytest.fixture
def current_user(source_game):
    """Current user matching the game host, with a distinct database user id."""
    user = MagicMock()
    user.discord_id = source_game.host.discord_id
    user.id = CURRENT_USER_DB_ID
    cu = MagicMock(spec=auth_schemas.CurrentUser)
    cu.user = user
    cu.access_token = "mock_token"
    return cu


@pytest.fixture
def role_service():
    """Mock role service."""
    return MagicMock()


@pytest.fixture
def game_service():
    """Build a GameService with all dependencies mocked."""
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    execute_result = MagicMock()
    execute_result.scalar_one = MagicMock(return_value=MagicMock(participants=[]))
    db.execute = AsyncMock(return_value=execute_result)

    return GameService(
        db=db,
        discord_client=AsyncMock(),
        participant_resolver=AsyncMock(),
        channel_resolver=AsyncMock(),
    )


def _make_clone_request(**overrides) -> CloneGameRequest:
    defaults: dict = {"scheduled_at": CLONE_AT}
    defaults.update(overrides)
    return CloneGameRequest(**defaults)


def _new_game_mock(game_id: str = "new-game-uuid") -> MagicMock:
    new_game = MagicMock(spec=game_model.GameSession)
    new_game.id = game_id
    new_game.thumbnail_id = None
    new_game.banner_image_id = None
    return new_game


@pytest.mark.asyncio
async def test_clone_game_source_not_found_raises_value_error(
    game_service, current_user, role_service
):
    """clone_game must raise ValueError when source game does not exist."""
    with patch.object(game_service, "get_game", new=AsyncMock(return_value=None)):
        with pytest.raises(ValueError, match="not found"):
            await game_service.clone_game(
                source_game_id="nonexistent-id",
                clone_data=_make_clone_request(),
                current_user=current_user,
                role_service=role_service,
            )


@pytest.mark.asyncio
async def test_clone_game_non_host_raises_value_error(
    game_service, source_game, current_user, role_service
):
    """clone_game must raise ValueError when user cannot manage the game."""
    with (
        patch.object(game_service, "get_game", new=AsyncMock(return_value=source_game)),
        patch("services.api.dependencies.permissions.can_manage_game", return_value=False),
        patch.object(game_service, "create_game", new=AsyncMock()) as mock_create,
    ):
        with pytest.raises(ValueError, match="permission"):
            await game_service.clone_game(
                source_game_id=source_game.id,
                clone_data=_make_clone_request(),
                current_user=current_user,
                role_service=role_service,
            )

    mock_create.assert_not_called()


@pytest.mark.asyncio
async def test_clone_game_builds_payload_from_source_when_no_overrides(
    game_service, source_game, current_user, role_service
):
    """With no clone_data overrides, every GameCreateRequest field falls back to source_game."""
    new_game = _new_game_mock()

    with (
        patch.object(game_service, "get_game", new=AsyncMock(return_value=source_game)),
        patch("services.api.dependencies.permissions.can_manage_game", return_value=True),
        patch.object(
            game_service, "create_game", new=AsyncMock(return_value=new_game)
        ) as mock_create,
    ):
        result = await game_service.clone_game(
            source_game_id=source_game.id,
            clone_data=_make_clone_request(),
            current_user=current_user,
            role_service=role_service,
        )

    assert result is new_game
    mock_create.assert_called_once()
    game_data = mock_create.call_args.args[0]
    assert isinstance(game_data, game_schemas.GameCreateRequest)
    assert game_data.template_id == source_game.template_id
    assert game_data.title == source_game.title
    assert game_data.scheduled_at == CLONE_AT
    assert game_data.description == source_game.description
    assert game_data.max_players == source_game.max_players
    assert game_data.expected_duration_minutes == source_game.expected_duration_minutes
    assert game_data.reminder_minutes == source_game.reminder_minutes
    assert game_data.where == source_game.where
    assert game_data.signup_instructions == source_game.signup_instructions
    assert game_data.initial_participants == []
    assert game_data.host is None
    assert game_data.signup_method == source_game.signup_method
    assert game_data.remind_host_rewards == source_game.remind_host_rewards
    assert game_data.reminders_as_dms == source_game.reminders_as_dms
    assert game_data.post_at is None
    assert game_data.recur_rule == source_game.recur_rule

    assert mock_create.call_args.kwargs["host_user_id"] == current_user.user.id
    assert mock_create.call_args.kwargs["default_host_user_id"] == source_game.host_id


@pytest.mark.asyncio
async def test_clone_game_overridden_fields_use_clone_data(
    game_service, source_game, current_user, role_service
):
    """Every clone_data override wins over the corresponding source_game value."""
    new_game = _new_game_mock()
    post_at_override = CLONE_AT - datetime.timedelta(hours=1)

    clone_data = _make_clone_request(
        title="New Title",
        description="New Description",
        max_players=5,
        expected_duration_minutes=90,
        reminder_minutes=[15],
        where="New Location",
        signup_instructions="New Instructions",
        participants=["@bob"],
        host="@carol",
        signup_method=SignupMethod.HOST_SELECTED.value,
        remind_host_rewards=False,
        reminders_as_dms=True,
        post_at=post_at_override,
        recur_rule="FREQ=DAILY",
    )

    with (
        patch.object(game_service, "get_game", new=AsyncMock(return_value=source_game)),
        patch("services.api.dependencies.permissions.can_manage_game", return_value=True),
        patch.object(
            game_service, "create_game", new=AsyncMock(return_value=new_game)
        ) as mock_create,
    ):
        await game_service.clone_game(
            source_game_id=source_game.id,
            clone_data=clone_data,
            current_user=current_user,
            role_service=role_service,
        )

    game_data = mock_create.call_args.args[0]
    assert game_data.title == "New Title"
    assert game_data.description == "New Description"
    assert game_data.max_players == 5
    assert game_data.expected_duration_minutes == 90
    assert game_data.reminder_minutes == [15]
    assert game_data.where == "New Location"
    assert game_data.signup_instructions == "New Instructions"
    assert game_data.initial_participants == ["@bob"]
    assert game_data.host == "@carol"
    assert game_data.signup_method == SignupMethod.HOST_SELECTED.value
    assert game_data.remind_host_rewards is False
    assert game_data.reminders_as_dms is True
    assert game_data.post_at == post_at_override
    assert game_data.recur_rule == "FREQ=DAILY"


@pytest.mark.asyncio
async def test_clone_game_omitting_host_decouples_default_host_from_requester(
    game_service, source_game, current_user, role_service
):
    """Omitting a host override passes source_game's host as default_host_user_id,
    while host_user_id (the bot-manager-permission-check subject) stays the requester.
    """
    new_game = _new_game_mock()

    with (
        patch.object(game_service, "get_game", new=AsyncMock(return_value=source_game)),
        patch("services.api.dependencies.permissions.can_manage_game", return_value=True),
        patch.object(
            game_service, "create_game", new=AsyncMock(return_value=new_game)
        ) as mock_create,
    ):
        await game_service.clone_game(
            source_game_id=source_game.id,
            clone_data=_make_clone_request(),
            current_user=current_user,
            role_service=role_service,
        )

    assert current_user.user.id != source_game.host_id, (
        "test fixture must use distinct requester/source-host ids to prove decoupling"
    )
    assert mock_create.call_args.kwargs["host_user_id"] == current_user.user.id
    assert mock_create.call_args.kwargs["default_host_user_id"] == source_game.host_id


@pytest.mark.asyncio
async def test_clone_game_copies_images_by_reference_when_source_has_images(
    game_service, source_game, current_user, role_service
):
    """When the source game has images, clone_game copies both ids onto the new game
    and increments both images' reference counts.
    """
    source_game.thumbnail_id = "thumbnail-uuid"
    source_game.banner_image_id = "banner-uuid"
    new_game = _new_game_mock()

    with (
        patch.object(game_service, "get_game", new=AsyncMock(return_value=source_game)),
        patch("services.api.dependencies.permissions.can_manage_game", return_value=True),
        patch.object(game_service, "create_game", new=AsyncMock(return_value=new_game)),
        patch("services.api.services.games.increment_image_ref", new=AsyncMock()) as mock_increment,
    ):
        result = await game_service.clone_game(
            source_game_id=source_game.id,
            clone_data=_make_clone_request(),
            current_user=current_user,
            role_service=role_service,
        )

    assert result.thumbnail_id == "thumbnail-uuid"
    assert result.banner_image_id == "banner-uuid"
    mock_increment.assert_any_await(game_service.db, "thumbnail-uuid")
    mock_increment.assert_any_await(game_service.db, "banner-uuid")
    assert mock_increment.await_count == 2
    game_service.db.add.assert_called_once_with(new_game)
    game_service.db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_clone_game_skips_image_ref_increment_when_source_has_no_images(
    game_service, source_game, current_user, role_service
):
    """When the source game has neither image, clone_game performs no image-related
    DB writes at all (both thumbnail_id and banner_image_id stay whatever create_game set).
    """
    source_game.thumbnail_id = None
    source_game.banner_image_id = None
    new_game = _new_game_mock()

    with (
        patch.object(game_service, "get_game", new=AsyncMock(return_value=source_game)),
        patch("services.api.dependencies.permissions.can_manage_game", return_value=True),
        patch.object(game_service, "create_game", new=AsyncMock(return_value=new_game)),
        patch("services.api.services.games.increment_image_ref", new=AsyncMock()) as mock_increment,
    ):
        await game_service.clone_game(
            source_game_id=source_game.id,
            clone_data=_make_clone_request(),
            current_user=current_user,
            role_service=role_service,
        )

    mock_increment.assert_not_awaited()
    game_service.db.add.assert_not_called()


@pytest.mark.asyncio
async def test_clone_game_propagates_create_game_value_error(
    game_service, source_game, current_user, role_service
):
    """A ValueError raised by the delegated create_game call (e.g. deleted template)
    propagates unchanged from clone_game.
    """
    with (
        patch.object(game_service, "get_game", new=AsyncMock(return_value=source_game)),
        patch("services.api.dependencies.permissions.can_manage_game", return_value=True),
        patch.object(
            game_service,
            "create_game",
            new=AsyncMock(side_effect=ValueError("Template not found: template-uuid")),
        ),
    ):
        with pytest.raises(ValueError, match="Template not found"):
            await game_service.clone_game(
                source_game_id=source_game.id,
                clone_data=_make_clone_request(),
                current_user=current_user,
                role_service=role_service,
            )


@pytest.mark.asyncio
async def test_clone_game_propagates_create_game_validation_error(
    game_service, source_game, current_user, role_service
):
    """A ValidationError raised by the delegated create_game call (unresolvable @mention)
    propagates unchanged from clone_game.
    """
    with (
        patch.object(game_service, "get_game", new=AsyncMock(return_value=source_game)),
        patch("services.api.dependencies.permissions.can_manage_game", return_value=True),
        patch.object(
            game_service,
            "create_game",
            new=AsyncMock(
                side_effect=resolver_module.ValidationError(
                    invalid_mentions=["@nobody"], valid_participants=[]
                )
            ),
        ),
    ):
        with pytest.raises(resolver_module.ValidationError):
            await game_service.clone_game(
                source_game_id=source_game.id,
                clone_data=_make_clone_request(),
                current_user=current_user,
                role_service=role_service,
            )


def _new_participant_mock(participant_id: str, user_id: str, discord_id: str) -> MagicMock:
    """Build a submitted-roster participant as create_game would return it."""
    participant = MagicMock(spec=participant_model.GameParticipant)
    participant.id = participant_id
    participant.user_id = user_id
    participant.user = MagicMock()
    participant.user.discord_id = discord_id
    return participant


def _schedules_from_add_calls(
    db_add_mock,
) -> tuple[list[ParticipantActionSchedule], list[NotificationSchedule]]:
    """Split a mocked db.add's call args into action/notification schedules."""
    added = [c[0][0] for c in db_add_mock.call_args_list]
    action_schedules = [a for a in added if isinstance(a, ParticipantActionSchedule)]
    notif_schedules = [a for a in added if isinstance(a, NotificationSchedule)]
    return action_schedules, notif_schedules


@pytest.mark.asyncio
async def test_clone_game_deadline_carryover_omitted_participant_gets_no_schedule(
    game_service, source_game, current_user, role_service
):
    """A source-confirmed participant left out of the submitted roster gets no
    deadline schedule, even with player_carryover=YES_WITH_DEADLINE.
    """
    new_game = _new_game_mock()
    new_game.participants = []  # host removed the previously-confirmed player

    clone_data = _make_clone_request(
        player_carryover=CarryoverOption.YES_WITH_DEADLINE,
        player_deadline=DEADLINE,
    )

    with (
        patch.object(game_service, "get_game", new=AsyncMock(return_value=source_game)),
        patch("services.api.dependencies.permissions.can_manage_game", return_value=True),
        patch.object(game_service, "create_game", new=AsyncMock(return_value=new_game)),
        patch.object(
            game_service,
            "_apply_deadline_carryover",
            new=AsyncMock(wraps=game_service._apply_deadline_carryover),
        ) as mock_apply,
    ):
        await game_service.clone_game(
            source_game_id=source_game.id,
            clone_data=clone_data,
            current_user=current_user,
            role_service=role_service,
        )

    mock_apply.assert_called_once_with(
        new_game=new_game, players_to_carry=[], waitlist_to_carry=[], clone_data=clone_data
    )
    action_schedules, notif_schedules = _schedules_from_add_calls(game_service.db.add)
    assert action_schedules == []
    assert notif_schedules == []


@pytest.mark.asyncio
async def test_clone_game_deadline_carryover_new_participant_gets_no_schedule(
    game_service, source_game, current_user, role_service
):
    """A submitted participant with no match in the source game's confirmed/overflow
    partition (a brand-new addition) gets no deadline schedule.
    """
    new_game = _new_game_mock()
    new_game.participants = [
        _new_participant_mock("new-participant-uuid", "new-user-uuid", "new-user-discord")
    ]

    clone_data = _make_clone_request(
        player_carryover=CarryoverOption.YES_WITH_DEADLINE,
        player_deadline=DEADLINE,
    )

    with (
        patch.object(game_service, "get_game", new=AsyncMock(return_value=source_game)),
        patch("services.api.dependencies.permissions.can_manage_game", return_value=True),
        patch.object(game_service, "create_game", new=AsyncMock(return_value=new_game)),
        patch.object(
            game_service,
            "_apply_deadline_carryover",
            new=AsyncMock(wraps=game_service._apply_deadline_carryover),
        ) as mock_apply,
    ):
        await game_service.clone_game(
            source_game_id=source_game.id,
            clone_data=clone_data,
            current_user=current_user,
            role_service=role_service,
        )

    mock_apply.assert_called_once_with(
        new_game=new_game, players_to_carry=[], waitlist_to_carry=[], clone_data=clone_data
    )
    action_schedules, notif_schedules = _schedules_from_add_calls(game_service.db.add)
    assert action_schedules == []
    assert notif_schedules == []


@pytest.mark.asyncio
async def test_clone_game_deadline_carryover_excludes_group_regardless_of_match(
    game_service, source_game, current_user, role_service
):
    """player_carryover=NO excludes the confirmed-player group entirely, even
    when the source-confirmed player is resubmitted; the waitlist group (set to
    YES_WITH_DEADLINE) is unaffected and still gets scheduled.
    """
    new_player = _new_participant_mock("new-participant-player", "user1-uuid", "player1-discord")
    new_waitlisted = _new_participant_mock(
        "new-participant-waitlist", "user2-uuid", "player2-discord"
    )
    new_game = _new_game_mock()
    new_game.participants = [new_player, new_waitlisted]

    clone_data = _make_clone_request(
        player_carryover=CarryoverOption.NO,
        waitlist_carryover=CarryoverOption.YES_WITH_DEADLINE,
        waitlist_deadline=DEADLINE,
    )

    with (
        patch.object(game_service, "get_game", new=AsyncMock(return_value=source_game)),
        patch("services.api.dependencies.permissions.can_manage_game", return_value=True),
        patch.object(game_service, "create_game", new=AsyncMock(return_value=new_game)),
    ):
        await game_service.clone_game(
            source_game_id=source_game.id,
            clone_data=clone_data,
            current_user=current_user,
            role_service=role_service,
        )

    action_schedules, notif_schedules = _schedules_from_add_calls(game_service.db.add)
    assert [a.participant_id for a in action_schedules] == ["new-participant-waitlist"]
    assert [n.participant_id for n in notif_schedules] == ["new-participant-waitlist"]


@pytest.mark.asyncio
async def test_clone_game_deadline_carryover_full_round_trip_schedules_both_groups(
    game_service, source_game, current_user, role_service
):
    """With both groups resubmitted and both set to YES_WITH_DEADLINE, every
    resubmitted source-confirmed/waitlisted participant gets a deadline schedule.
    """
    new_player = _new_participant_mock("new-participant-player", "user1-uuid", "player1-discord")
    new_waitlisted = _new_participant_mock(
        "new-participant-waitlist", "user2-uuid", "player2-discord"
    )
    new_game = _new_game_mock()
    new_game.participants = [new_player, new_waitlisted]

    clone_data = _make_clone_request(
        player_carryover=CarryoverOption.YES_WITH_DEADLINE,
        player_deadline=DEADLINE,
        waitlist_carryover=CarryoverOption.YES_WITH_DEADLINE,
        waitlist_deadline=DEADLINE,
    )

    with (
        patch.object(game_service, "get_game", new=AsyncMock(return_value=source_game)),
        patch("services.api.dependencies.permissions.can_manage_game", return_value=True),
        patch.object(game_service, "create_game", new=AsyncMock(return_value=new_game)),
    ):
        await game_service.clone_game(
            source_game_id=source_game.id,
            clone_data=clone_data,
            current_user=current_user,
            role_service=role_service,
        )

    action_schedules, notif_schedules = _schedules_from_add_calls(game_service.db.add)
    assert {a.participant_id for a in action_schedules} == {
        "new-participant-player",
        "new-participant-waitlist",
    }
    assert {n.participant_id for n in notif_schedules} == {
        "new-participant-player",
        "new-participant-waitlist",
    }


@pytest.mark.asyncio
async def test_apply_deadline_carryover_creates_action_and_notification_schedules(
    game_service, source_game
):
    """_apply_deadline_carryover creates one action schedule and one
    notification per participant.
    """
    source_player = source_game.participants[0]

    new_participant = MagicMock(spec=participant_model.GameParticipant)
    new_participant.id = "new-participant-uuid"
    new_participant.user_id = source_player.user_id

    new_game = MagicMock(spec=game_model.GameSession)
    new_game.id = "new-game-uuid"
    new_game.scheduled_at = CLONE_AT
    new_game.participants = [new_participant]

    clone_data = CloneGameRequest(
        scheduled_at=CLONE_AT,
        player_carryover=CarryoverOption.YES_WITH_DEADLINE,
        player_deadline=DEADLINE,
    )

    await game_service._apply_deadline_carryover(
        new_game=new_game,
        players_to_carry=[source_player],
        waitlist_to_carry=[],
        clone_data=clone_data,
    )

    add_calls = game_service.db.add.call_args_list
    action_schedules = [
        c[0][0] for c in add_calls if isinstance(c[0][0], ParticipantActionSchedule)
    ]
    notif_schedules = [c[0][0] for c in add_calls if isinstance(c[0][0], NotificationSchedule)]

    assert len(action_schedules) == 1, "Exactly one ParticipantActionSchedule must be created"
    sched = action_schedules[0]
    assert sched.participant_id == new_participant.id
    assert sched.game_id == new_game.id
    assert sched.action == "drop"
    assert sched.action_time == DEADLINE.replace(tzinfo=None)

    assert len(notif_schedules) == 1, "Exactly one NotificationSchedule must be created"
    notif = notif_schedules[0]
    assert notif.participant_id == new_participant.id
    assert notif.notification_type == "clone_confirmation"


@pytest.mark.asyncio
async def test_apply_deadline_carryover_sends_pg_notify(game_service, source_game):
    """_apply_deadline_carryover sends pg_notify to wake the scheduler service."""
    source_player = source_game.participants[0]

    new_participant = MagicMock(spec=participant_model.GameParticipant)
    new_participant.id = "new-participant-uuid"
    new_participant.user_id = source_player.user_id

    new_game = MagicMock(spec=game_model.GameSession)
    new_game.id = "new-game-uuid"
    new_game.scheduled_at = CLONE_AT
    new_game.participants = [new_participant]

    clone_data = CloneGameRequest(
        scheduled_at=CLONE_AT,
        player_carryover=CarryoverOption.YES_WITH_DEADLINE,
        player_deadline=DEADLINE,
    )

    await game_service._apply_deadline_carryover(
        new_game=new_game,
        players_to_carry=[source_player],
        waitlist_to_carry=[],
        clone_data=clone_data,
    )

    execute_calls = game_service.db.execute.call_args_list
    notify_calls = [
        c
        for c in execute_calls
        if hasattr(c.args[0], "text") and "participant_action_schedule_changed" in c.args[0].text
    ]
    assert len(notify_calls) == 1, "pg_notify for participant_action_schedule_changed must be sent"


@pytest.mark.asyncio
async def test_apply_deadline_carryover_skips_when_no_deadline_carryover(game_service, source_game):
    """_apply_deadline_carryover does nothing when neither carryover is YES_WITH_DEADLINE."""
    new_game = MagicMock(spec=game_model.GameSession)
    new_game.id = "new-game-uuid"
    new_game.participants = []

    clone_data = CloneGameRequest(
        scheduled_at=CLONE_AT,
        player_carryover=CarryoverOption.YES,
        waitlist_carryover=CarryoverOption.NO,
    )

    await game_service._apply_deadline_carryover(
        new_game=new_game,
        players_to_carry=list(source_game.participants),
        waitlist_to_carry=[],
        clone_data=clone_data,
    )

    game_service.db.add.assert_not_called()


@pytest.mark.asyncio
async def test_apply_deadline_carryover_skips_missing_participant(game_service, source_game):
    """_apply_deadline_carryover logs a warning and skips participants not found in new game."""
    source_player = source_game.participants[0]

    new_game = MagicMock(spec=game_model.GameSession)
    new_game.id = "new-game-uuid"
    new_game.scheduled_at = CLONE_AT
    new_game.participants = []  # No matching participant in new game

    clone_data = CloneGameRequest(
        scheduled_at=CLONE_AT,
        player_carryover=CarryoverOption.YES_WITH_DEADLINE,
        player_deadline=DEADLINE,
    )

    await game_service._apply_deadline_carryover(
        new_game=new_game,
        players_to_carry=[source_player],
        waitlist_to_carry=[],
        clone_data=clone_data,
    )

    game_service.db.add.assert_not_called()
