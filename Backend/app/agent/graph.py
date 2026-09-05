"""LangGraph recovery agent orchestration."""
from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.graph import StateGraph, END
from app.agent.state import RecoveryState
from app.agent.nodes.ingest_event import ingest_event
from app.agent.nodes.analyze_failure import analyze_failure
from app.agent.nodes.assess_recoverability import assess_recoverability
from app.agent.nodes.decide_strategy import decide_strategy
from app.agent.nodes.policy_check import policy_check
from app.agent.nodes.execute_action import execute_action
from app.agent.nodes.evaluate_result import evaluate_result
from app.agent.nodes.adapt_strategy import adapt_strategy
from app.agent.nodes.finalize_recovery import finalize_recovery
from app.repositories.recovery_repository import RecoveryRepository
from app.core.logging import get_logger

logger = get_logger("agent.graph")


def _route_after_evaluate(state: RecoveryState) -> str:
    if state.get("next_step") == "adapt":
        return "adapt"
    return "finalize"


def _should_finalize(state: RecoveryState) -> bool:
    return state.get("next_step") == "finalize" or state.get("final_status") is not None


class RecoveryAgent:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(RecoveryState)

        def _make_node(node_func):
            async def _node(state: RecoveryState) -> RecoveryState:
                return await self._run_node(node_func, state)
            return _node

        workflow.add_node("ingest_event", _make_node(ingest_event))
        workflow.add_node("analyze_failure", _make_node(analyze_failure))
        workflow.add_node("assess_recoverability", _make_node(assess_recoverability))
        workflow.add_node("decide_strategy", _make_node(decide_strategy))
        workflow.add_node("policy_check", _make_node(policy_check))
        workflow.add_node("execute_action", _make_node(execute_action))
        workflow.add_node("evaluate_result", _make_node(evaluate_result))
        workflow.add_node("adapt_strategy", _make_node(adapt_strategy))
        workflow.add_node("finalize_recovery", _make_node(finalize_recovery))

        workflow.set_entry_point("ingest_event")
        workflow.add_edge("ingest_event", "analyze_failure")
        workflow.add_edge("analyze_failure", "assess_recoverability")
        workflow.add_edge("assess_recoverability", "decide_strategy")
        workflow.add_edge("decide_strategy", "policy_check")

        workflow.add_conditional_edges(
            "policy_check",
            lambda state: "finalize_recovery" if _should_finalize(state) else "execute_action",
            {"finalize_recovery": "finalize_recovery", "execute_action": "execute_action"},
        )

        workflow.add_edge("execute_action", "evaluate_result")
        workflow.add_conditional_edges(
            "evaluate_result",
            _route_after_evaluate,
            {"finalize": "finalize_recovery", "adapt": "adapt_strategy"},
        )
        workflow.add_edge("adapt_strategy", "policy_check")
        workflow.add_edge("finalize_recovery", END)

        return workflow.compile()

    async def _run_node(self, node_func, state: RecoveryState) -> RecoveryState:
        return await node_func(state, self.session)

    async def run(self, recovery_id: int, operator_override: bool = False) -> RecoveryState:
        recovery_repo = RecoveryRepository(self.session)
        recovery = await recovery_repo.get_by_id(recovery_id)

        if not recovery:
            logger.error("recovery_not_found", recovery_id=recovery_id)
            return {"error": "Recovery not found"}

        await recovery_repo.update(recovery, status="analyzing")

        initial_state: RecoveryState = {
            "payment_id": recovery.payment_id,
            "recovery_id": recovery.id,
            "strategy": recovery.current_strategy or "",
            "current_step": recovery.current_step or "",
            "operator_override": operator_override,
        }

        try:
            result = await self.graph.ainvoke(initial_state, {"recursion_limit": 20})
            await self.session.commit()
            logger.info(
                "recovery_agent_completed",
                recovery_id=recovery_id,
                final_status=result.get("final_status", "unknown"),
            )
            return result
        except Exception as e:
            logger.error("recovery_agent_failed", recovery_id=recovery_id, error=str(e))
            await recovery_repo.update(recovery, status="exhausted", explanation=f"Agent error: {str(e)}")
            await self.session.commit()
            return {"error": str(e), "final_status": "exhausted"}
