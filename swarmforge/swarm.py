"""Mixture-of-experts swarm: diverge -> adversarially critique -> judge -> human gate.

The swarm only *recommends*. It never executes actions. Irreversible recommendations
stop at `awaiting_approval` until a human signs off.
"""
from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor

from .audit import AuditLog
from .llm import LLM, LLMError
from .schemas import Critique, Expert, Proposal, ProposalRecord, RunResult, RunStatus, Verdict

DEFAULT_EXPERTS: list[Expert] = [
    Expert(name="first_principles", lens="Strip the goal to physical/economic fundamentals and rebuild from there."),
    Expert(name="pragmatist", lens="Use proven, boring tools and best practices; optimise for shipping this week."),
    Expert(name="contrarian", lens="Assume the obvious approach is wrong; propose the strongest alternative."),
    Expert(name="safety_engineer", lens="Optimise for reliability, failure containment, and reversibility."),
    Expert(name="user_advocate", lens="Optimise for the real human who must benefit; ignore vanity metrics."),
]

MAX_EXPERTS = 8
MAX_GOAL_CHARS = 4000

GROUND_RULES = (
    "Be concrete and honest. Do not claim capabilities you lack, fabricate data, or project revenue "
    "without evidence. Mark a plan irreversible if any step spends real money, deletes data, publishes, "
    "contacts people, or signs anything."
)


class Swarm:
    def __init__(self, llm: LLM, audit: AuditLog, experts: list[Expert] | None = None, max_workers: int = 5):
        experts = experts or DEFAULT_EXPERTS
        if not 1 <= len(experts) <= MAX_EXPERTS:
            raise ValueError(f"need 1..{MAX_EXPERTS} experts")
        self.llm, self.audit, self.experts, self.max_workers = llm, audit, experts, max_workers

    def _propose(self, expert: Expert, goal: str) -> ProposalRecord:
        try:
            p = self.llm.structured(
                f"You are the {expert.name} expert. {expert.lens} {GROUND_RULES}",
                f"Goal:\n{goal}\n\nPropose the single best next step plan.",
                Proposal,
            )
            return ProposalRecord(expert=expert.name, proposal=p)
        except LLMError as e:
            return ProposalRecord(expert=expert.name, error=str(e))

    def _critique(self, goal: str, rec: ProposalRecord) -> ProposalRecord:
        if rec.proposal is None:
            return rec
        try:
            rec.critique = self.llm.structured(
                "You are a red-team reviewer. Find what would make this plan fail, be unsafe, or be dishonest. "
                "Score harshly; a plan with any fatal flaw scores at most 3.",
                f"Goal:\n{goal}\n\nPlan:\n{rec.proposal.model_dump_json(indent=2)}",
                Critique,
            )
        except LLMError as e:
            rec.error = f"critique failed: {e}"
        return rec

    def run(self, goal: str) -> RunResult:
        goal = goal.strip()
        if not goal or len(goal) > MAX_GOAL_CHARS:
            raise ValueError(f"goal must be 1..{MAX_GOAL_CHARS} characters")
        run_id = uuid.uuid4().hex[:12]
        self.audit.append("run_started", {"id": run_id, "goal": goal})

        with ThreadPoolExecutor(self.max_workers) as pool:
            recs = list(pool.map(lambda e: self._propose(e, goal), self.experts))
            recs = list(pool.map(lambda r: self._critique(goal, r), recs))

        viable = [(i, r) for i, r in enumerate(recs) if r.proposal and r.critique and not r.critique.fatal_flaws]
        if not viable:
            res = RunResult(id=run_id, goal=goal, status=RunStatus.failed, proposals=recs,
                            error="No proposal survived critique; refine the goal.")
            self.audit.append("run_failed", {"id": run_id, "reason": res.error})
            return res

        slate = "\n\n".join(
            f"[{i}] by {r.expert} (critic score {r.critique.score}/10)\n{r.proposal.model_dump_json()}\n"
            f"Critique: {r.critique.model_dump_json()}" for i, r in viable
        )
        try:
            verdict = self.llm.structured(
                "You are the judge. Pick the proposal most likely to achieve the goal safely, weighing critic "
                "scores but thinking for yourself. Report the strongest dissent honestly.",
                f"Goal:\n{goal}\n\nCandidates (use the bracketed index):\n{slate}",
                Verdict,
            )
        except LLMError as e:
            res = RunResult(id=run_id, goal=goal, status=RunStatus.failed, proposals=recs, error=f"judge failed: {e}")
            self.audit.append("run_failed", {"id": run_id, "reason": res.error})
            return res

        valid = {i for i, _ in viable}
        if verdict.chosen_index not in valid:  # judge hallucinated an index -> fall back to best score
            verdict.chosen_index = max(viable, key=lambda t: t[1].critique.score)[0]
        chosen = recs[verdict.chosen_index].proposal
        status = RunStatus.completed if chosen.reversible else RunStatus.awaiting_approval
        res = RunResult(id=run_id, goal=goal, status=status, proposals=recs, verdict=verdict, chosen=chosen)
        self.audit.append("run_finished", {"id": run_id, "status": status.value, "chosen": chosen.title})
        return res
