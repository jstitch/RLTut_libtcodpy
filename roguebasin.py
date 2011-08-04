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

# rooms
ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30

# monsters
MAX_ROOM_MONSTERS = 3

# FOV
FOV_ALGO = 0 # default FOV algorithm
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 10

# console refresh rate
LIMIT_FPS = 20


# ---
# COLORS
# ---
color_dark_wall = libtcod.Color(0, 0, 100)
color_light_wall = libtcod.Color(130, 110, 50)
color_dark_ground = libtcod.Color(50, 50, 150)
color_light_ground = libtcod.Color(200, 180, 50)


# ---
# OBJS
# ---
# An object in the map
class Object:
    # this is a generic object: the player, a monster, an item, the stairs...
    # it's always represented by a character on screen.
    def __init__(self, x, y, char, name, color, blocks=False):
        self.x = x
        self.y = y
        self.char = char
        self.name = name
        self.color = color
        self.blocks = blocks

    def move(self, dx, dy):
        if not is_blocked(self.x + dx, self.y + dy):
            # move by the given amount
            self.x += dx
            self.y += dy

    def draw(self):
        if libtcod.map_is_in_fov(fov_map, self.x, self.y):
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
        self.explored = False

        # by default, if a tile is blocked, it also blocks sight
        if block_sight is None: block_sight = blocked
        self.block_sight = block_sight

# A rectangle class
class Rect:
    # a rectangle on the map, used to characterize a room
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h

    def center(self):
        center_x = (self.x1 + self.x2) / 2
        center_y = (self.y1 + self.y2) / 2
        return (center_x, center_y)

    def intersect(self, other):
        # returns true if this rectangle intersects with another one
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)


# ---
# FUNCS
# ---
# Handle key input
def handle_keys():
    global game_state

#    key = libtcod.console_check_for_keypress() # real-time
    key = libtcod.console_wait_for_keypress(True) # turn-based

    if key.vk == libtcod.KEY_ENTER and libtcod.KEY_ALT:
        # Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    elif key.vk == libtcod.KEY_ESCAPE:
        return 'exit' # exit game

    # movement keys
    if game_state == 'playing':
        if libtcod.console_is_key_pressed(libtcod.KEY_UP):
            player_move_or_attack(0, -1)
        elif libtcod.console_is_key_pressed(libtcod.KEY_DOWN):
            player_move_or_attack(0, 1)
        elif libtcod.console_is_key_pressed(libtcod.KEY_LEFT):
            player_move_or_attack(-1, 0)
        elif libtcod.console_is_key_pressed(libtcod.KEY_RIGHT):
            player_move_or_attack(1, 0)
        else:
            return 'didnt-take-turn'

# The player takes an action such as move or attack
def player_move_or_attack(dx, dy):
    global fov_recompute, player

    # the coordinates the player is moving to/attacking
    x = player.x + dx
    y = player.y + dy

    # try to find an attackable object there
    target = None
    for object in objects:
        if object.x == x and object.y == y:
            target = object
            break

    # attack if target found, move otherwise
    if target is not None:
        print 'The ' + target.name + ' laughs at your puny efforts to attack him!'
    else:
        player.move(dx, dy)
        fov_recompute = True

# Place objects in some room
def place_objects(room):
    global objects
    
    # choose random number of monsters
    num_monsters = libtcod.random_get_int(0, 0, MAX_ROOM_MONSTERS)

    for i in range(num_monsters):
        # choose random spot for this monster
        x = libtcod.random_get_int(0, room.x1, room.x2)
        y = libtcod.random_get_int(0, room.y1, room.y2)

        if not is_blocked(x, y):
            # chances: 80% orc, 20% troll
            choice = libtcod.random_get_int(0, 0, 100)
            if choice < 80: # orc
                # create an orc
                monster = Object(x, y, 'o', 'orc', libtcod.desaturated_green)
            else:
                # create a troll
                monster = Object(x, y, 'T', 'troll', libtcod.darker_green)

            objects.append(monster)

# Create map
def make_map():
    global map, player

    # fill map with "blocked" tiles
    map = [[ Tile(True)
        for y in range(MAP_HEIGHT) ]
            for x in range(MAP_WIDTH) ]

    rooms = []
    num_rooms = 0

    for r in range(MAX_ROOMS):
        # random width and height
        w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        # random position without going out of the boundaries of the map
        x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
        y = libtcod.random_get_int(0, 0, MAP_HEIGHT - h - 1)

        # "Rect" class makes rectangles easier to work with
        new_room = Rect(x, y, w, h)

        # run through the other rooms and see if they intersect with this one
        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break

        if not failed:
            # this means there are no intersections, so the room is valid

            # "paint" it to the map's tiles
            create_room(new_room)

            # add some contents to this room, such as monsters
            place_objects(new_room)

            # center coordinates of new room, will be useful later
            (new_x, new_y) = new_room.center()

            if num_rooms == 0:
                # this is the first room, where the player starts at
                player.x = new_x
                player.y = new_y

            else:
                # all rooms after the first:
                # connect it to the previous room with a tunnel

                # center coordinates of previous room
                (prev_x, prev_y) = rooms[num_rooms - 1].center()

                # draw a coin (random number that is either 0 or 1)
                if libtcod.random_get_int(0, 0, 1) == 1:
                    # first move horizontally, then vertically
                    create_h_tunnel(prev_x, new_x, prev_y)
                    create_v_tunnel(prev_y, new_y, new_x)
                else:
                    # first move vertically, then horizontally
                    create_v_tunnel(prev_y, new_y, prev_x)
                    create_h_tunnel(prev_x, new_x, new_y)

            # finally, append the new room to the list
            rooms.append(new_room)
            num_rooms += 1

# Create a room in the map
def create_room(room):
    global map

    # go through the tiles in the rectangle and make them passable
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            map[x][y].blocked = False
            map[x][y].block_sight = False

# Create horizontal tunnel
def create_h_tunnel(x1, x2, y):
    global map

    for x in range(min(x1, x2), max(x1, x2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False

# Create vertical tunnel
def create_v_tunnel(y1, y2, x):
    global map

    for y in range(min(y1, y2), max(y1, y2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False

# Test if tile is blocked
def is_blocked(x, y):
    global map, objects
    
    # first test the map tile
    if map[x][y].blocked:
        return True

    # now check for any blocking objects
    for object in objects:
        if object.blocks and object.x == x and object.y == y:
            return True

    return False

# Render all
def render_all():
    global color_light_wall, color_light_ground
    global color_dark_wall, color_dark_ground
    global fov_map, fov_recompute
    global player, map

    # draw the map
    if fov_recompute:
        # recompute FOV if needed (the player moved or something)
        fov_recompute = False
        libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)

        # go through all tiles, and set their background color according to the FOV
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                visible = libtcod.map_is_in_fov(fov_map, x, y)
                wall = map[x][y].block_sight
                if not visible:
                    # it's out of the player's FOV
                    # if it's not visible right now, the player can only see it if it's explored
                    if map[x][y].explored:
                        if wall:
                            libtcod.console_set_back(con, x, y, color_dark_wall, libtcod.BKGND_SET )
                        else:
                            libtcod.console_set_back(con, x, y, color_dark_ground, libtcod.BKGND_SET )
                else:
                    # it's visible
                    # explore the tile since it is visible right now
                    map[x][y].explored = True
                    if wall:
                        libtcod.console_set_back(con, x, y, color_light_wall, libtcod.BKGND_SET )
                    else:
                        libtcod.console_set_back(con, x, y, color_light_ground, libtcod.BKGND_SET )

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


# ---
# GLOBALS
# ---
# Player init
player = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, '@', 'player', libtcod.white)

# Objects Array
objects = [player]

# Map
make_map()

# FOV Map
fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
for y in range(MAP_HEIGHT):
    for x in range(MAP_WIDTH):
        libtcod.map_set_properties(fov_map, x, y, not map[x][y].blocked, not map[x][y].block_sight)

fov_recompute = True

# Game states
game_state = 'playing'
player_action = None


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
    player_action = handle_keys()
    if player_action == 'exit':
        break

    # let monsters take their turn
    if game_state == 'playing' and player_action != 'didnt-take-turn':
        for object in objects:
            if object != player:
                print 'The ' + object.name + ' growls!'
