from fastapi import APIRouter, Depends

from app.adaptive_engine.strategy_selector import select_strategy
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.strategy import StrategyDecision, StrategyEvaluationRequest

router = APIRouter(prefix="/strategy", tags=["Adaptive Strategy"])


@router.post(
    "/preview",
    response_model=StrategyDecision,
    summary="Dry run: which strategy would the engine choose? (changes nothing)",
)
def preview_strategy(
    body: StrategyEvaluationRequest,
    user: User = Depends(get_current_user),
):
    return select_strategy(body.requirements, body.assessment, body.sources)