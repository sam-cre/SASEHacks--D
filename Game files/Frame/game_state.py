from Cards.Cards import Card

class GameState:
    def __init__(self, player):
        self.player = player
        self.monsters_defeated = 0
        self.damage_multiplier = 1.0
        # Initialize with 2 basic cards as requested
        self.cards_in_deck = [
            Card("Strike", 10, 15, "Basic attack"),
            Card("Strike", 10, 15, "Basic attack")
        ]
        self.cards_in_hand = []
