from __future__ import annotations

from dataclasses import dataclass, field

from src.core.refusal import RefusalError
from src.core.values import ValueSpec

from .stage import Stage, StageType


@dataclass
class StageChain:
    stages: list[Stage]

    total_losses: dict[str, ValueSpec] = field(default_factory=dict)
    total_exergy_destruction: ValueSpec | None = None

    def validate(self) -> None:
        # empty list => refusepython -c "from src.core.scenario import Scenario; print('OK')"
        if not self.stages:
            raise RefusalError(
                code="REFUSE_STAGECHAIN_EMPTY",
                user_message="Cannot build system because StageChain has no stages.",
                why="A system must contain at least one Stage.",
                missing=["stage_chain.stages"],
            )

        # must end with DELIVER stage
        if self.stages[-1].stage_type != StageType.DELIVER:
            raise RefusalError(
                code="REFUSE_STAGECHAIN_NO_DELIVER",
                user_message="Cannot build system because StageChain does not end with a DELIVER stage.",
                why="Functional unit requires delivered useful heat at the DH boundary, so the chain must end with DELIVER.",
                missing=["last_stage.stage_type = DELIVER"],
            )

