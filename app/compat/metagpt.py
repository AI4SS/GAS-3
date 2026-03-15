from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

METAGPT_AVAILABLE = False
METAGPT_IMPORT_ERROR = ""

try:
    from metagpt.actions import Action as MetaGPTAction
    from metagpt.config2 import config as metagpt_config
    from metagpt.environment import Environment as MetaGPTEnvironment
    from metagpt.roles import Role as MetaGPTRole
    from metagpt.schema import Message as MetaGPTMessage
    from metagpt.team import Team as MetaGPTTeam

    ActionBase = MetaGPTAction
    RoleBase = MetaGPTRole
    EnvironmentBase = MetaGPTEnvironment
    MessageBase = MetaGPTMessage
    TeamBase = MetaGPTTeam
    config = metagpt_config
    METAGPT_AVAILABLE = True
except Exception as exc:  # pragma: no cover - runtime-dependent
    METAGPT_IMPORT_ERROR = str(exc)

    class ActionBase(BaseModel):
        name: str = ""

        async def run(self, *args, **kwargs):
            raise NotImplementedError

    class MessageBase(BaseModel):
        content: str
        role: str = "assistant"
        cause_by: str = ""
        sent_from: str = ""
        send_to: set[str] = Field(default_factory=lambda: {"<all>"})
        instruct_content: dict[str, Any] | None = None

    class RoleBase(BaseModel):
        name: str = ""
        profile: str = ""
        goal: str = ""
        constraints: str = ""
        actions: list[Any] = Field(default_factory=list)

        def set_actions(self, actions: list[Any]) -> None:
            self.actions = actions

    class EnvironmentBase(BaseModel):
        desc: str = ""

    class TeamBase(BaseModel):
        env: Any | None = None

        def hire(self, roles: list[Any]) -> None:
            return None

    class _Config:
        def __init__(self) -> None:
            self.data: dict[str, Any] = {}

        def update_via_dict(self, data: dict[str, Any]) -> None:
            self.data.update(data)

    config = _Config()
