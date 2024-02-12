import pygame as pg

STANDARD_FONT = "Trebuchet MS"

# Colors for buttons.
BUTTON_STANDARD_COLOR = (15, 107, 54)
BUTTON_PRESSED_COLOR = (0, 57, 4)
BUTTON_DISABLED_COLOR = (44, 44, 44)

class Button:
    def __init__(self, screen, x, y, width, height, color, text, text_size, is_active) -> None:
        global SCREEN
        SCREEN = screen
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.text = text
        self.text_size = text_size
        self.is_active = is_active
        self.is_disabled = False
    
    def draw_button(self):
        if self.is_disabled:
            self.color = BUTTON_DISABLED_COLOR
        elif self.is_active:
            self.color = BUTTON_PRESSED_COLOR
        else:
            self.color = BUTTON_STANDARD_COLOR
        pg.draw.rect(SCREEN, self.color, (self.x, self.y, self.width+1, self.height+1))
        text_font = pg.font.SysFont(STANDARD_FONT, self.text_size)
        text_surface = text_font.render(self.text, True, (255, 255, 255))
        surface_width = pg.Surface.get_width(text_surface)
        surface_height = pg.Surface.get_height(text_surface)
        SCREEN.blit(text_surface, (self.x + self.width/2 - surface_width/2, self.y + self.height/2 - surface_height/2))
        self.draw_boundaries()

    def draw_boundaries(self):
        boundary_color = (30, 30, 30)
        boundary_width = 2
        pg.draw.line(SCREEN, boundary_color, (self.x, self.y), (self.x+self.width, self.y), boundary_width)
        pg.draw.line(SCREEN, boundary_color, (self.x+self.width, self.y), (self.x+self.width, self.y+self.height), boundary_width)
        pg.draw.line(SCREEN, boundary_color, (self.x+self.width, self.y+self.height), (self.x, self.y+self.height), boundary_width)
        pg.draw.line(SCREEN, boundary_color, (self.x, self.y+self.height), (self.x, self.y), boundary_width)