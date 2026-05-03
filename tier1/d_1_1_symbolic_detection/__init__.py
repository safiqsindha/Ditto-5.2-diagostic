from tier1.d_1_1_symbolic_detection import (
    pubg_rules,
    nba_rules,
    csgo_rules,
    rocket_league_rules,
    poker_rules,
)

DOMAIN_CHECKERS = {
    "pubg": pubg_rules.check_chain,
    "nba": nba_rules.check_chain,
    "csgo": csgo_rules.check_chain,
    "rocket_league": rocket_league_rules.check_chain,
    "poker": poker_rules.check_chain,
}

__all__ = ["DOMAIN_CHECKERS"]
