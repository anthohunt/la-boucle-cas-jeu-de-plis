# SPDX-License-Identifier: Apache-2.0
import unittest

from trickloop.bots import ParamBot, RandomBot, RuleBot, N_PARAMS
from trickloop.game import (KIND, N_CARDS, legal_cards, play_game, round_score, trick_winner, card_name)

C = {card_name(i): i for i in range(N_CARDS)}   # "coral3", "flag10", "escape1", "pirate2", "siren", "captain"


class TestRules(unittest.TestCase):
    def test_deck(self):
        self.assertEqual(len(set(card_name(i) for i in range(N_CARDS))), N_CARDS)
        self.assertEqual(sum(1 for k in KIND if k == "suit"), 40)

    def test_highest_of_lead_suit_wins(self):
        self.assertEqual(trick_winner([(0, C["coral3"]), (1, C["coral9"]), (2, C["anchor10"])]), 1)

    def test_trump_beats_lead_suit(self):
        self.assertEqual(trick_winner([(0, C["coral10"]), (1, C["flag1"]), (2, C["coral9"])]), 1)

    def test_escape_loses_unless_all_escape(self):
        self.assertEqual(trick_winner([(0, C["escape1"]), (1, C["coral2"])]), 1)
        self.assertEqual(trick_winner([(2, C["escape1"]), (0, C["escape2"])]), 2)

    def test_special_order(self):
        self.assertEqual(trick_winner([(0, C["flag10"]), (1, C["pirate1"]), (2, C["siren"])]), 1)      # pirate > siren
        self.assertEqual(trick_winner([(0, C["pirate1"]), (1, C["captain"]), (2, C["coral1"])]), 1)    # captain > pirate
        self.assertEqual(trick_winner([(0, C["captain"]), (1, C["siren"]), (2, C["pirate1"])]), 1)     # siren > captain
        self.assertEqual(trick_winner([(0, C["coral10"]), (1, C["siren"])]), 1)                        # siren > suit

    def test_must_follow_suit_but_specials_are_free(self):
        hand = [C["coral2"], C["anchor5"], C["pirate1"], C["escape1"]]
        plays = [(0, C["coral9"])]
        self.assertEqual(sorted(legal_cards(hand, plays)), sorted([C["coral2"], C["pirate1"], C["escape1"]]))
        self.assertEqual(sorted(legal_cards([C["anchor5"], C["flag2"]], plays)), sorted([C["anchor5"], C["flag2"]]))
        self.assertEqual(sorted(legal_cards(hand, [])), sorted(hand))

    def test_scoring(self):
        self.assertEqual(round_score(0, 0, 4), 40)
        self.assertEqual(round_score(0, 1, 4), -40)
        self.assertEqual(round_score(2, 2, 5), 40)
        self.assertEqual(round_score(3, 1, 5), -20)


class TestGames(unittest.TestCase):
    def test_game_is_deterministic(self):
        a = play_game([RuleBot() for _ in range(4)], "seed-x")
        b = play_game([RuleBot() for _ in range(4)], "seed-x")
        self.assertEqual(a.scores, b.scores)
        self.assertNotEqual(a.scores, play_game([RuleBot() for _ in range(4)], "seed-y").scores)

    def test_every_trick_is_won_exactly_once(self):
        res = play_game([RuleBot() for _ in range(4)], 3)
        for r, rl in enumerate(res.rounds, 1):
            self.assertEqual(sum(rl.won), r)

    def test_bots_always_play_legal_cards(self):
        th = [0.3 * ((i * 7) % 5 - 2) for i in range(N_PARAMS)]
        for g in range(60):
            bots = [RuleBot(), ParamBot(th, "full"), RandomBot(g), ParamBot(th, "basic", "rules")]
            play_game(bots, f"legal-{g}")     # raises ValueError on an illegal card


if __name__ == "__main__":
    unittest.main()
