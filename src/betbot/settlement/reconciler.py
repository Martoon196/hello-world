"""Settlement reconciliation.

Two fact sources feed the same interface:
  - delayed-key results poller  -> SettlementFact (authoritative for WIN/LOSE/VOID)
  - BFBM bet-log import         -> PlacementFact (authoritative for matched price/stake/P&L)

If BFBM's export hasn't arrived, we settle ESTIMATED at the validated price and
flag needs_review; when actuals arrive later, a correction ledger row replaces
the estimate — ledger rows are append-only, never edited.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from betbot.config import tunables
from betbot.db.repo import Repo
from betbot.notify import messages

log = logging.getLogger(__name__)


@dataclass
class PlacementFact:
    tip_id: int
    matched_price_cents: int
    matched_stake_cents: int
    net_pnl_cents: int | None = None   # BFBM's own P&L if present in the export


@dataclass
class SettlementFact:
    bet_id: int
    result: str                        # WON | LOST | VOID


class Reconciler:
    def __init__(self, repo: Repo, notifier):
        self.repo = repo
        self.notifier = notifier

    async def settle_from_result(self, fact: SettlementFact) -> None:
        """Called by the results poller when a market closes."""
        bet = self.repo.get_bet(fact.bet_id)
        if bet is None or bet["state"].startswith("SETTLED"):
            return
        cfg = tunables().settlement

        # For a LAY bet, our bet WINS when the runner LOSES.
        our_result = fact.result
        if bet["side"] == "LAY" and fact.result in ("WON", "LOST"):
            our_result = "LOST" if fact.result == "WON" else "WON"

        has_actuals = bet["matched_price_cents"] is not None
        price_cents = bet["matched_price_cents"] or bet["validated_price_cents"]
        stake_cents = bet["matched_stake_cents"] or bet["stake_cents"]

        gross, commission, net = self._bet_pnl(bet["side"], our_result, stake_cents, price_cents,
                                               cfg.commission_pct)
        state = {"WON": "SETTLED_WON", "LOST": "SETTLED_LOST", "VOID": "SETTLED_VOID"}[our_result]
        source = "bfbm_export" if has_actuals else "delayed_api_estimated"
        self.repo.settle_bet(fact.bet_id, state=state, result=our_result,
                             gross_pnl_cents=gross, commission_cents=commission,
                             net_pnl_cents=net, settlement_source=source,
                             needs_review=not has_actuals)
        balance = self.repo.append_ledger(delta_cents=net, reason="bet_settlement",
                                          bet_id=fact.bet_id,
                                          note=None if has_actuals else "estimated")
        tip = self.repo.get_tip(bet["tip_id"])
        await self.notifier.send(messages.bet_settled(
            horse=tip["horse_name"] if tip else "?", result=our_result,
            net_pnl_cents=net, bankroll_cents=balance, estimated=not has_actuals))

    async def apply_placement_facts(self, facts: list[PlacementFact]) -> int:
        """Called by the BFBM bet-log import. Fills actuals; corrects estimates."""
        cfg = tunables().settlement
        applied = 0
        for fact in facts:
            bet = self.repo._one(
                "SELECT * FROM bets WHERE tip_id=? AND state != 'ABORTED' ORDER BY id DESC LIMIT 1",
                (fact.tip_id,))
            if bet is None:
                log.warning("BFBM export references unknown tip_id %s", fact.tip_id)
                continue
            applied += 1
            self.repo.set_bet_placement(bet["id"], fact.matched_price_cents, fact.matched_stake_cents)

            # If already settled on an estimate, recompute at actuals and post a correction.
            if bet["state"].startswith("SETTLED") and bet["settlement_source"] == "delayed_api_estimated":
                gross, commission, net = self._bet_pnl(
                    bet["side"], bet["result"], fact.matched_stake_cents,
                    fact.matched_price_cents, cfg.commission_pct)
                delta = net - (bet["net_pnl_cents"] or 0)
                self.repo.settle_bet(bet["id"], state=bet["state"], result=bet["result"],
                                     gross_pnl_cents=gross, commission_cents=commission,
                                     net_pnl_cents=net, settlement_source="bfbm_export",
                                     matched_price_cents=fact.matched_price_cents,
                                     matched_stake_cents=fact.matched_stake_cents,
                                     needs_review=False)
                if delta != 0:
                    self.repo.append_ledger(delta_cents=delta, reason="settlement_correction",
                                            bet_id=bet["id"],
                                            note=f"estimate corrected by {delta/100:+.2f}")
        return applied

    @staticmethod
    def _bet_pnl(side: str, our_result: str, stake_cents: int, price_cents: int,
                 commission_pct: float) -> tuple[int, int, int]:
        """(gross, commission, net) from OUR bet's perspective."""
        if our_result == "VOID":
            return 0, 0, 0
        if side == "BACK":
            gross = int(stake_cents * (price_cents - 100) / 100) if our_result == "WON" else -stake_cents
        else:  # LAY: we won the backer's stake, or we pay the liability
            gross = stake_cents if our_result == "WON" else -int(stake_cents * (price_cents - 100) / 100)
        commission = int(gross * commission_pct) if gross > 0 else 0
        return gross, commission, gross - commission
