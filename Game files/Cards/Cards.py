import random

class Card:
    def __init__(self, name, damage_min, damage_max, description=""):
        self.name = name
        self.damage_min = damage_min
        self.damage_max = damage_max
        self.description = description
        
    def roll_damage(self):
        return random.randint(self.damage_min, self.damage_max)