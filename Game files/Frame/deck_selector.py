"""
Deck Selector screen — lists all .json files in FlashcardUploads/
and lets the player click one to start the game with that deck.
"""
import os
import pygame

class DeckSelector:
    def __init__(self, screen, game_state, uploads_dir):
        self.screen = screen
        self.game_state = game_state
        self.uploads_dir = uploads_dir
        self.deck_files = []
        self.deck_rects = []
        self.selected = False
        self._scan_decks()

    def _scan_decks(self):
        """Find all .json files in the uploads directory."""
        self.deck_files = []
        if os.path.isdir(self.uploads_dir):
            for f in sorted(os.listdir(self.uploads_dir)):
                if f.lower().endswith(".json"):
                    self.deck_files.append(f)
        self._build_rects()

    def _build_rects(self):
        """Build clickable rectangles for each deck."""
        self.deck_rects = []
        start_y = 200
        for i, name in enumerate(self.deck_files):
            rect = pygame.Rect(200, start_y + i * 60, 400, 45)
            self.deck_rects.append(rect)

    def handle_event(self, event):
        """Check for clicks on deck buttons. Returns True if a deck was selected."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.deck_rects):
                if rect.collidepoint(event.pos):
                    deck_path = os.path.join(self.uploads_dir, self.deck_files[i])
                    self.game_state.selected_deck_path = deck_path
                    self.selected = True
                    return True
        return False

    def draw(self):
        """Draw the deck selection screen."""
        self.screen.fill((10, 10, 30))

        # Title
        title_font = pygame.font.SysFont(None, 52)
        title = title_font.render("Choose Your Flashcard Deck", True, (100, 255, 150))
        title_rect = title.get_rect(center=(400, 100))
        self.screen.blit(title, title_rect)

        # Subtitle
        sub_font = pygame.font.SysFont(None, 26)
        sub = sub_font.render("Questions will be drawn from this deck during battles", True, (180, 180, 180))
        sub_rect = sub.get_rect(center=(400, 145))
        self.screen.blit(sub, sub_rect)

        if not self.deck_files:
            warn = sub_font.render("No .json decks found in FlashcardUploads!", True, (255, 100, 100))
            self.screen.blit(warn, (200, 250))
            return

        # Deck buttons
        btn_font = pygame.font.SysFont(None, 30)
        for i, name in enumerate(self.deck_files):
            rect = self.deck_rects[i]
            mouse_pos = pygame.mouse.get_pos()
            hover = rect.collidepoint(mouse_pos)

            bg = (60, 60, 120) if hover else (40, 40, 80)
            border = (150, 200, 255) if hover else (100, 100, 160)

            pygame.draw.rect(self.screen, bg, rect, border_radius=8)
            pygame.draw.rect(self.screen, border, rect, 2, border_radius=8)

            # Deck name (strip .json)
            display_name = name.replace(".json", "")
            text = btn_font.render(display_name, True, (255, 255, 255))
            text_rect = text.get_rect(center=rect.center)
            self.screen.blit(text, text_rect)
