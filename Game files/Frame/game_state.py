class GameState:
    def __init__(self, player):
        self.player = player
        self.monsters_defeated = 0
        self.damage_multiplier = 1.0
        self.cards_in_deck = []
        self.cards_in_hand = []
