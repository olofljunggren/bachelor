import pygame as pg

STANDARD_FONT = "Trebuchet MS"

class PopupField():
    def __init__(self, screen, x, y, width, height, color, text_size, border_line_boundary_width, collapsed_window_descriptive_text) -> None:
        global SCREEN
        SCREEN = screen
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.list_of_texts = [collapsed_window_descriptive_text]
        self.list_of_texts.append("")
        self.text_size = text_size
        self.border_line_boundary_width = border_line_boundary_width
        self.is_active = False
        self.collapsed_window_text_above = collapsed_window_descriptive_text
        _, SCREEN_HEIGHT = pg.display.get_surface().get_size()
        self.popup_height = SCREEN_HEIGHT/3
        self.text_font = pg.font.SysFont(STANDARD_FONT, self.text_size)
        
        self.num_rows_to_display_mimized = 1
        displacement = 15
        self.max_num_rows_to_display_mimized = int(height/(displacement+text_size))

    def draw_popup_field(self):

        # Draw background
        pg.draw.rect(SCREEN, self.color, (self.x+self.border_line_boundary_width, self.y+self.border_line_boundary_width, \
                     self.width-self.border_line_boundary_width, self.height-self.border_line_boundary_width))

        displacement = 10
        if self.is_active:
            pg.draw.rect(SCREEN, self.color, (self.x, self.y-self.popup_height, self.width, self.height+self.popup_height)) # Background
            for idx, text in enumerate(self.list_of_texts):
                text_surface = self.text_font.render(text, True, (255, 255, 255))
                SCREEN.blit(text_surface, (self.x + displacement, self.y + displacement - self.popup_height + (self.text_size + 10)*idx))
            self.draw_popup_field_outlines()
        else:
            text_surface_above = self.text_font.render(self.collapsed_window_text_above, True, (255, 255, 255))
            SCREEN.blit(text_surface_above, (self.x + displacement, self.y + displacement))

            for i in range(self.num_rows_to_display_mimized):
                text_surf = self.text_font.render(self.list_of_texts[i+1], True, (255, 255, 255))
                SCREEN.blit(text_surf, (self.x + displacement, self.y + displacement + 1.2*self.text_size*(i+1) + 6))

    def add_to_text_list(self, text):
        self.list_of_texts.insert(1, text)
        self.num_rows_to_display_mimized = min(self.num_rows_to_display_mimized+1, self.max_num_rows_to_display_mimized)


    def draw_popup_field_outlines(self):
        boundary_color = (30, 30, 30)
        pg.draw.line(SCREEN, boundary_color, (self.x, self.y + self.height), (self.x, self.y - self.popup_height), self.border_line_boundary_width)                     # Left boundary
        pg.draw.line(SCREEN, boundary_color, (self.x, self.y - self.popup_height), (self.x + self.width, self.y - self.popup_height), self.border_line_boundary_width)  # Top boundary
        pg.draw.line(SCREEN, boundary_color, (self.x + self.width, self.y - self.popup_height), (self.x + self.width, self.y), self.border_line_boundary_width)         # Right boundary