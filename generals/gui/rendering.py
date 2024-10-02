import pygame
import numpy as np
import generals.core.config as c

from .properties import Properties


class Renderer:
    def __init__(self, properties: Properties):
        """
        Initialize the pygame GUI
        """
        pygame.init()
        pygame.display.set_caption("Generals")
        pygame.key.set_repeat(500, 64)

        self.properties = properties

        self.game = self.properties.game

        self.agent_data = self.properties.agent_data
        self.agent_fov = self.properties.agent_fov

        self.grid_height = self.properties.grid_height
        self.grid_width = self.properties.grid_width
        self.display_grid_width = self.properties.display_grid_width
        self.display_grid_height = self.properties.display_grid_height
        self.right_panel_width = self.properties.right_panel_width

        ############
        # Surfaces #
        ############
        window_width = self.display_grid_width + self.right_panel_width
        window_height = self.display_grid_height + 1

        # Main window
        self.screen = pygame.display.set_mode(
            (window_width, window_height), pygame.HWSURFACE | pygame.DOUBLEBUF
        )
        # Scoreboard
        self.right_panel = pygame.Surface((self.right_panel_width, window_height))
        self.score_cols = {}
        for col in ["Agent", "Army", "Land"]:
            size = (c.GUI_CELL_WIDTH, c.GUI_ROW_HEIGHT)
            if col == "Agent":
                size = (2 * c.GUI_CELL_WIDTH, c.GUI_ROW_HEIGHT)
            self.score_cols[col] = [pygame.Surface(size) for _ in range(3)]

        self.info_panel = {
            "time": pygame.Surface((self.right_panel_width / 2, c.GUI_ROW_HEIGHT)),
            "speed": pygame.Surface((self.right_panel_width / 2, c.GUI_ROW_HEIGHT)),
        }
        # Game area and tiles
        self.game_area = pygame.Surface(
            (self.display_grid_width, self.display_grid_height)
        )
        self.tiles = [
            [
                pygame.Surface((c.SQUARE_SIZE, c.SQUARE_SIZE))
                for _ in range(self.grid_width)
            ]
            for _ in range(self.grid_height)
        ]

        self._mountain_img = pygame.image.load(
            str(c.MOUNTAIN_PATH), "png"
        ).convert_alpha()
        self._general_img = pygame.image.load(
            str(c.GENERAL_PATH), "png"
        ).convert_alpha()
        self._city_img = pygame.image.load(str(c.CITY_PATH), "png").convert_alpha()

        self._font = pygame.font.Font(c.FONT_PATH, c.FONT_SIZE)

    def render(self, fps=None):
        self.render_grid()
        self.render_stats()
        pygame.display.flip()
        if fps:
            self.properties.clock.tick(fps)

    def render_cell_text(self, cell, text, fg_color=c.BLACK, bg_color=c.WHITE):
        """
        Draw a text in the middle of the cell with given foreground and background colors

        Args:
            cell: cell to draw
            text: text to write on the cell
            fg_color: foreground color of the text
            bg_color: background color of the cell
        """
        center = (cell.get_width() // 2, cell.get_height() // 2)

        text = self._font.render(text, True, fg_color)
        if bg_color:
            cell.fill(bg_color)
        cell.blit(text, text.get_rect(center=center))

    def render_stats(self):
        """
        Draw player stats and additional info on the right panel
        """
        names = self.game.agents
        player_stats = self.game.get_infos()

        # Write names
        for i, name in enumerate(["Agent"] + names):
            color = (
                self.agent_data[name]["color"] if name in self.agent_data else c.WHITE
            )
            # add opacity to the color, where color is a tuple (r,g,b)
            if name in self.agent_fov and not self.agent_fov[name]:
                color = tuple([int(0.5 * rgb) for rgb in color])
            self.render_cell_text(self.score_cols["Agent"][i], name, bg_color=color)

        # Write other columns
        for i, col in enumerate(["Army", "Land"]):
            self.render_cell_text(self.score_cols[col][0], col)
            for j, name in enumerate(names):
                # Give darkish color if agents FoV is off
                color = c.WHITE
                if name in self.agent_fov and not self.agent_fov[name]:
                    color = (128, 128, 128)
                self.render_cell_text(
                    self.score_cols[col][j + 1],
                    str(player_stats[name][col.lower()]),
                    bg_color=color,
                )

        # Blit each right_panel cell to the right_panel surface
        for i, col in enumerate(["Agent", "Army", "Land"]):
            for j, cell in enumerate(self.score_cols[col]):
                rect_dim = (0, 0, cell.get_width(), cell.get_height())
                pygame.draw.rect(cell, c.BLACK, rect_dim, 1)

                position = ((i + 1) * c.GUI_CELL_WIDTH, j * c.GUI_ROW_HEIGHT)
                if col == "Agent":
                    position = (0, j * c.GUI_ROW_HEIGHT)
                self.right_panel.blit(cell, position)

        info_text = {
            "time": f"Time: {str(self.game.time // 2) + ('.' if self.game.time % 2 == 1 else '')}",
            "speed": "Paused" if self.properties.paused else f"Speed: {str(1 / self.properties.game_speed)}x",
        }

        # Write additional info
        for i, key in enumerate(["time", "speed"]):
            self.render_cell_text(self.info_panel[key], info_text[key])

            rect_dim = (
                0,
                0,
                self.info_panel[key].get_width(),
                self.info_panel[key].get_height(),
            )
            pygame.draw.rect(self.info_panel[key], c.BLACK, rect_dim, 1)

            self.right_panel.blit(
                self.info_panel[key], (i * 2 * c.GUI_CELL_WIDTH, 3 * c.GUI_ROW_HEIGHT)
            )
        # Render right_panel on the screen
        self.screen.blit(self.right_panel, (self.display_grid_width, 0))

    def render_grid(self):
        """
        Render the game grid
        """
        agents = self.game.agents
        # Maps of all owned and visible cells
        owned_map = np.zeros((self.grid_height, self.grid_width), dtype=np.bool)
        visible_map = np.zeros((self.grid_height, self.grid_width), dtype=np.bool)
        for agent in agents:
            ownership = self.game.channels.ownership[agent]
            owned_map = np.logical_or(owned_map, ownership)
            if self.agent_fov[agent]:
                visibility = self.game.visibility_channel(ownership)
                visible_map = np.logical_or(visible_map, visibility)

        # Helper maps for not owned and invisible cells
        not_owned_map = np.logical_not(owned_map)
        invisible_map = np.logical_not(visible_map)

        # Draw background of visible owned squares
        for agent in agents:
            ownership = self.game.channels.ownership[agent]
            visible_ownership = np.logical_and(ownership, visible_map)
            self.draw_channel(visible_ownership, self.agent_data[agent]["color"])

        # Draw visible generals
        visible_generals = np.logical_and(self.game.channels.general, visible_map)
        self.draw_images(visible_generals, self._general_img)

        # Draw background of visible but not owned squares
        visible_not_owned = np.logical_and(visible_map, not_owned_map)
        self.draw_channel(visible_not_owned, c.WHITE)

        # Draw background of squares in fog of war
        self.draw_channel(invisible_map, c.FOG_OF_WAR)

        # Draw background of visible mountains
        visible_mountain = np.logical_and(self.game.channels.mountain, visible_map)
        self.draw_channel(visible_mountain, c.VISIBLE_MOUNTAIN)

        # Draw mountains (even if they are not visible)
        self.draw_images(self.game.channels.mountain, self._mountain_img)

        # Draw background of visible neutral cities
        visible_cities = np.logical_and(self.game.channels.city, visible_map)
        visible_cities_neutral = np.logical_and(
            visible_cities, self.game.channels.ownership_neutral
        )
        self.draw_channel(visible_cities_neutral, c.NEUTRAL_CASTLE)

        # Draw invisible cities as mountains
        invisible_cities = np.logical_and(self.game.channels.city, invisible_map)
        self.draw_images(invisible_cities, self._mountain_img)

        # Draw visible cities
        self.draw_images(visible_cities, self._city_img)

        # Draw nonzero army counts on visible squares
        visible_army = self.game.channels.army * visible_map
        visible_army_indices = self.game.channel_to_indices(visible_army)
        for i, j in visible_army_indices:
            self.render_cell_text(
                self.tiles[i][j],
                str(int(visible_army[i, j])),
                fg_color=c.WHITE,
                bg_color=None,  # Transparent background
            )

        # Blit tiles to the self.game_area
        for i, j in np.ndindex(self.grid_height, self.grid_width):
            self.game_area.blit(
                self.tiles[i][j], (j * c.SQUARE_SIZE, i * c.SQUARE_SIZE)
            )
        self.screen.blit(self.game_area, (0, 0))

    def draw_channel(self, channel, color: tuple[int, int, int]):
        """
        Draw background and borders (left and top) for grid tiles of a given channel
        """
        for i, j in self.game.channel_to_indices(channel):
            self.tiles[i][j].fill(color)
            pygame.draw.line(self.tiles[i][j], c.BLACK, (0, 0), (0, c.SQUARE_SIZE), 1)
            pygame.draw.line(self.tiles[i][j], c.BLACK, (0, 0), (c.SQUARE_SIZE, 0), 1)

    def draw_images(self, channel, image):
        """
        Draw images on grid tiles of a given channel
        """
        for i, j in self.game.channel_to_indices(channel):
            self.tiles[i][j].blit(image, (3, 2))