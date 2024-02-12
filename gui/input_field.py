import pygame as pg

STANDARD_FONT = "Trebuchet MS"

class InputField:
    def __init__(self, screen, x, y, width, height, background_color, text_size, fps) -> None:
        global SCREEN, FRAMES_PER_SECOND
        SCREEN = screen
        FRAMES_PER_SECOND = fps
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text_size = text_size
        self.background_color = background_color
        self.current_text = ">>> "
        self.field_is_active = False
        self.text_font = pg.font.SysFont(STANDARD_FONT, self.text_size)
        self.text_surface = self.text_font.render(self.current_text, True, (255, 255, 255))

        # Blinker setup
        self.blinker_is_active = False
        self.blinker_timer = 0
        self.blinker_index = 4

    def draw_input_field_and_blinker(self):
        pg.draw.rect(SCREEN, self.background_color, (self.x, self.y, self.width, self.height))
        self.text_surface = self.text_font.render(self.current_text, True, (255, 255, 255))
        
        surface_blinker = self.text_font.render(self.current_text[:self.blinker_index], True, (255, 255, 255))
        surface_width_blinker = pg.Surface.get_width(surface_blinker)
        surface_height = pg.Surface.get_height(self.text_surface)
        
        SCREEN.blit(self.text_surface, (self.x + 6, self.y + self.height/2 - surface_height/2 + 15))
        self.draw_blinker(surface_width_blinker, surface_height)        

    def update_blinker(self):
        self.blinker_timer += 1

        blinking_duration_frames = 30*FRAMES_PER_SECOND/60
        if self.blinker_timer > blinking_duration_frames:
            self.blinker_is_active = not self.blinker_is_active
            self.blinker_timer = 0

    def draw_blinker(self, surface_width, surface_height):
        if self.blinker_is_active and self.field_is_active:
            blinker_font = pg.font.SysFont(STANDARD_FONT, self.text_size)
            blinker_surface = blinker_font.render("|", True, (255, 255, 255))
            SCREEN.blit(blinker_surface, (self.x + surface_width + 3, self.y + self.height/2 - surface_height/2 + 13))

