from __future__ import annotations

from pydantic import BaseModel, Field

from app.actions.analyze_group_response import AnalyzeGroupResponse
from app.actions.generate_comment import GenerateComment
from app.actions.quantize_behavior import QuantizeBehavior
from app.compat.metagpt import METAGPT_AVAILABLE, METAGPT_IMPORT_ERROR, RoleBase
from app.schema.agent_state import GroupProfile, GroupRoundResult, GroupState
from app.schema.news_state import NewsState
from app.schema.simulation import RoundContext
from app.services.llm import LLMGateway
class GroupAgent(RoleBase, BaseModel):
    profile_name: str = "GroupAgent"
    goal: str = "Simulate a group agent in the GA-S3 social network setting"
    constraints: str = "Preserve the original paper logic while remaining runnable"
    group_profile: GroupProfile
    group_state: GroupState = Field(default_factory=GroupState)
    runtime_notes: list[str] = Field(default_factory=list)

    def model_post_init(self, __context) -> None:
        self.name = self.group_profile.name
        self.profile = self.group_profile.name
        if METAGPT_AVAILABLE:
            try:
                self.set_actions([AnalyzeGroupResponse, GenerateComment, QuantizeBehavior])
            except Exception:
                self.runtime_notes.append("MetaGPT actions not fully initialized; using internal execution path.")
        else:
            self.runtime_notes.append(f"MetaGPT unavailable: {METAGPT_IMPORT_ERROR}")

    async def run_round(self, news_state: NewsState, round_ctx: RoundContext, llm_gateway: LLMGateway) -> GroupRoundResult:
        analyzer = AnalyzeGroupResponse(llm_gateway=llm_gateway)
        commenter = GenerateComment()
        quantizer = QuantizeBehavior()

        self.group_state = await analyzer.run(self.group_profile, self.group_state, news_state, round_ctx)
        comment = await commenter.run(self.group_profile, self.group_state, news_state, round_ctx, llm_gateway=llm_gateway)
        metrics = await quantizer.run(self.group_profile, self.group_state, news_state, round_ctx, llm_gateway=llm_gateway)
        self.group_state.last_comment = comment

        return GroupRoundResult(
            group_id=self.group_profile.id,
            group_name=self.group_profile.name,
            layer=self.group_profile.layer,
            hierarchy_path=self.group_profile.hierarchy_path,
            emotion=self.group_state.emotion,
            attitude=self.group_state.attitude,
            polarity=self.group_state.polarity,
            internal_groups=self.group_state.internal_groups,
            metrics=metrics,
            comment=comment,
        )
