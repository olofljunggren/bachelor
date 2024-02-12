import pygame as pg

STANDARD_FONT = "Trebuchet MS"

class TextField():
    def __init__(self, screen, x, y, text, text_size) -> None:
        global SCREEN
        SCREEN = screen
        self.x = x
        self.y = y
        self.text = text
        self.text_size = text_size

    def draw_text_field(self):
        text_font = pg.font.SysFont(STANDARD_FONT, self.text_size)
        text_surface = text_font.render(self.text, True, (255, 255, 255))
        SCREEN.blit(text_surface, (self.x, self.y))