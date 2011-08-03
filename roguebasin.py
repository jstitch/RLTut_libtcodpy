#!/usr/bin/python2

# Roguebasin tutorial

# libtcod library
import libtcodpy as libtcod

# game constants
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50

# console refresh rate
LIMIT_FPS = 20

# ---
# OBJS
# ---
class Object:
    # this is a generic object: the player, a monster, an item, the stairs...
    # it's always represented by a character on screen.
    def __init__(self, x, y, char, color):
        self.x = x
        self.y = y
        self.char = char
        self.color = color

    def move(self, dx, dy):
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


# ---
# FUNCS
# ---
def handle_keys():
    global player

    # real-time RL
#    key = libtcod.console_check_for_keypress()
    # turn-based RL
    key = libtcod.console_wait_for_keypress(True)

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


# ---
# INITS
# ---
# init font
libtcod.console_set_custom_font('arial12x12.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
# init root screen
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'python/libtcod tutorial', False)
# off-screen main console
con = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)
# for real-time RL
#libtcod.sys_set_fps(LIMIT_FPS)

# player init
player = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, '@', libtcod.white)
npc = Object(SCREEN_WIDTH/2 - 5, SCREEN_HEIGHT/2, '@', libtcod.yellow)

# Objects Array
objects = [npc, player]

# ---
# MAIN
# ---
while not libtcod.console_is_window_closed():
    # foreground color
    libtcod.console_set_foreground_color(con, libtcod.white)

    # draw all objects
    for object in objects:
        object.draw()

    # blit off-screen consoles to root one
    libtcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)
    # flush data to screen
    libtcod.console_flush()

    # clear all objects
    for object in objects:
        object.clear()

    # handle keys and exit game if needed
    exit = handle_keys()
    if exit:
        break
