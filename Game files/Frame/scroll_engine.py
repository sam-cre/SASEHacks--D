import pygame

class ScrollEngine:
    def __init__(self):
        self.scrolling = False
        self.offset = 0
        self.speed = 2

    def start_scroll(self):
        self.scrolling = True

    def stop_scroll(self):
        self.scrolling = False

    def update(self):
        if self.scrolling:
            self.offset += self.speed

    def draw_background(self, screen, bg_image=None):
        if bg_image:
            # Assuming bg_image is wider than screen
            rel_x = self.offset % bg_image.get_rect().width
            screen.blit(bg_image, (-rel_x, 0))
            if rel_x > 0:
                screen.blit(bg_image, (bg_image.get_rect().width - rel_x, 0))
        else:
            # Draw placeholder scrolling grid
            screen.fill((50, 50, 80))
            for i in range(0, screen.get_width() + 40, 40):
                x = i - (self.offset % 40)
                pygame.draw.line(screen, (100, 100, 150), (x, 0), (x, screen.get_height()), 1)
