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
            sw, sh = screen.get_size()
            iw, ih = bg_image.get_size()
            # Clamp offset so we never scroll past the right edge
            max_scroll = max(0, iw - sw)
            x = -min(self.offset, max_scroll)
            # Centre vertically if image is taller than screen
            y = -max(0, (ih - sh) // 2)
            screen.blit(bg_image, (x, y))
        else:
            # Draw placeholder scrolling grid
            screen.fill((50, 50, 80))
            for i in range(0, screen.get_width() + 40, 40):
                x = i - (self.offset % 40)
                pygame.draw.line(screen, (100, 100, 150), (x, 0), (x, screen.get_height()), 1)
