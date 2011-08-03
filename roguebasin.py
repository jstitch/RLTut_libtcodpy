#!/usr/bin/python2

# Roguebasin tutorial

# libtcod library
import libtcodpy as libtcod

# ---
# CONSTS
# ---
# Game Constants
# screen
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
# map
MAP_WIDTH = 80
MAP_HEIGHT = 45

# console refresh rate
LIMIT_FPS = 20


# ---
# COLORS
# ---
color_dark_wall = libtcod.Color(0, 0, 100)
color_dark_ground = libtcod.Color(50, 50, 150)


# ---
# OBJS
# ---
# An object in the map
class Object:
    # this is a generic object: the player, a monster, an item, the stairs...
    # it's always represented by a character on screen.
    def __init__(self, x, y, char, color):
        self.x = x
        self.y = y
        self.char = char
        self.color = color

    def move(self, dx, dy):
        if not map[self.x + dx][self.y + dy].blocked:
            # move by the given amount
            self.x += dx
            self.y += dy

    def draw(self):
        # set the color and then draw the character that represents this object at its position
        libtcod.console_set_foreground_color(con, self.color)
        libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)

    def clear(self):
        # erase the character that represents this object
        libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)

# A tile in the map
class Tile:
    # a tile of the map and its properties
    def __init__(self, blocked, block_sight = None):
        self.blocked = blocked

        # by default, if a tile is blocked, it also blocks sight
        if block_sight is None: block_sight = blocked
        self.block_sight = block_sight


# ---
# FUNCS
# ---
# Handle key input
def handle_keys():
    global player

#    key = libtcod.console_check_for_keypress() # real-time
    key = libtcod.console_wait_for_keypress(True) # turn-based

    if key.vk == libtcod.KEY_ENTER and libtcod.KEY_ALT:
        # Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    elif key.vk == libtcod.KEY_ESCAPE:
        return True  # exit game

    # movement keys
    if libtcod.console_is_key_pressed(libtcod.KEY_UP):
        player.move(0, -1)
    elif libtcod.console_is_key_pressed(libtcod.KEY_DOWN):
        player.move(0, 1)
    elif libtcod.console_is_key_pressed(libtcod.KEY_LEFT):
        player.move(-1, 0)
    elif libtcod.console_is_key_pressed(libtcod.KEY_RIGHT):
        player.move(1, 0)

# Create map
def make_map():
    global map

    # fill map with "unblocked" tiles
    map = [[ Tile(False)
        for y in range(MAP_HEIGHT) ]
            for x in range(MAP_WIDTH) ]

# Render all
def render_all():
    global color_dark_wall, color_dark_ground

    # draw the map
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            wall = map[x][y].block_sight
            if wall:
                libtcod.console_set_back(con, x, y, color_dark_wall, libtcod.BKGND_SET )
            else:
                libtcod.console_set_back(con, x, y, color_dark_ground, libtcod.BKGND_SET )

    # draw all objects in the list
    for object in objects:
        object.draw()

    # blit off-screen consoles to root one
    libtcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)


# ---
# INITS
# ---
# init font
libtcod.console_set_custom_font('arial12x12.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
# for real-time RL
#libtcod.sys_set_fps(LIMIT_FPS)
# init root screen
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'python/libtcod tutorial', False)
# off-screen main console
con = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)

# Player init
player = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, '@', libtcod.white)

# Add an NPC
npc = Object(SCREEN_WIDTH/2 - 5, SCREEN_HEIGHT/2, '@', libtcod.yellow)

# Objects Array
objects = [npc, player]

# Map
make_map()
map[30][22].blocked = True
map[30][22].block_sight = True
map[50][22].blocked = True
map[50][22].block_sight = True


# ---
# MAIN
# ---
while not libtcod.console_is_window_closed():
    # draw
    render_all()
    # flush data to screen
    libtcod.console_flush()

    # clear all objects
    for object in objects:
        object.clear()

    # handle keys and exit game if needed
    exit = handle_keys()
    if exit:
        break
