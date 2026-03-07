import random
import pygame

class Enemy:
    def __init__(self, name, hp, max_hp, attack, x=600, y=300):
        self.name = name
        self.hp = hp
        self.max_hp = max_hp
        self.attack = attack
        self.x = x
        self.y = y
        self.rect = pygame.Rect(self.x, self.y, 50, 50)
        
    def is_alive(self):
        return self.hp > 0
        
    def take_damage(self, amount):
        self.hp = max(0, self.hp - amount)
        
    def roll_attack(self):
        # A little variance
        return max(1, self.attack + random.randint(-2, 2))
        
    def draw(self, screen):
        if not self.is_alive():
            return
        pygame.draw.rect(screen, (255, 0, 0), self.rect)
        # HP bar
        hp_ratio = self.hp / self.max_hp
        pygame.draw.rect(screen, (255, 0, 0), (self.x, self.y - 10, 50, 5))
        pygame.draw.rect(screen, (0, 255, 0), (self.x, self.y - 10, 50 * hp_ratio, 5))
        
        # Draw Name
        font = pygame.font.SysFont(None, 24)
        name_text = font.render(self.name, True, (255, 255, 255))
        screen.blit(name_text, (self.x, self.y - 30))