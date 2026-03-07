import pygame

class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.max_hp = 100
        self.hp = 100
        self.defense = 0
        self.rect = pygame.Rect(self.x, self.y, 40, 40)
    
    def draw(self, screen):
        pygame.draw.rect(screen, (0, 255, 0), self.rect)
        # HP bar
        hp_ratio = self.hp / self.max_hp
        pygame.draw.rect(screen, (255, 0, 0), (self.x, self.y - 10, 40, 5))
        pygame.draw.rect(screen, (0, 255, 0), (self.x, self.y - 10, 40 * max(0, hp_ratio), 5))
