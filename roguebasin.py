#!/usr/bin/python2

# Roguebasin tutorial

# libtcod library
import libtcodpy as libtcod

# game constants
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50

# console refresh rate
LIMIT_FPS = 20

# FUNCS
def handle_keys():
    global playerx, playery

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
        playery -= 1
    elif libtcod.console_is_key_pressed(libtcod.KEY_DOWN):
        playery += 1
    elif libtcod.console_is_key_pressed(libtcod.KEY_LEFT):
        playerx -= 1
    elif libtcod.console_is_key_pressed(libtcod.KEY_RIGHT):
        playerx += 1


# INITS
# init font
libtcod.console_set_custom_font('arial12x12.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
# init root screen
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'python/libtcod tutorial', False)
# for real-time RL
#libtcod.sys_set_fps(LIMIT_FPS)

# player init
playerx = SCREEN_WIDTH/2
playery = SCREEN_HEIGHT/2

# MAIN
while not libtcod.console_is_window_closed():
    # foreground color
    libtcod.console_set_foreground_color(0, libtcod.white)

    # print character
    libtcod.console_print_left(0, 1, 1, libtcod.BKGND_NONE, '@')

    # flush data to screen
    libtcod.console_flush()

    # clean player mess
    libtcod.console_print_left(0, playerx, playery, libtcod.BKGND_NONE, ' ')
    # handle keys and exit game if needed
    exit = handle_keys()
    if exit:
        break
