#!/usr/bin/python

# Roguebasin Roguelike Development Tutorial with Libtcod and Python
# http://roguebasin.roguelikedevelopment.org/index.php/Complete_Roguelike_Tutorial,_using_python%2Blibtcod

# ---
# Imports
# ---

import math
import textwrap
import shelve
import libtcodpy as libtcod


# ---
# CONSTS
# ---

# Screen
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
# Map
MAP_WIDTH = 80
MAP_HEIGHT = 43
#  Rooms
ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30

# Game
#  Healing potion
HEAL_AMOUNT = 40
#  Lightning bolt scroll
LIGHTNING_DAMAGE = 40
LIGHTNING_RANGE = 5
#  Confusion
CONFUSE_NUM_TURNS = 10
CONFUSE_RANGE = 8
#  Fireball
FIREBALL_RADIUS = 3
FIREBALL_DAMAGE = 25
# Experience and level-ups
LEVEL_UP_BASE = 200
LEVEL_UP_FACTOR = 150

# FOV
FOV_ALGO = 0 # default FOV algorithm
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 10

# GUI
#  Bottom panel
BAR_WIDTH = 20
PANEL_HEIGHT = 7
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT
#  Message bar
MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1
#  Inventory
INVENTORY_WIDTH = 50
# Levels
LEVEL_SCREEN_WIDTH = 40
CHARACTER_SCREEN_WIDTH = 30

# Console refresh rate
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
    def __init__(self, x, y, char, name, color, blocks=False, always_visible=False,
                 fighter=None, ai=None, item=None):
        self.x = x
        self.y = y
        self.char = char
        self.name = name
        self.color = color
        self.blocks = blocks
        self.always_visible = always_visible
        # components
        self.fighter = fighter
        if self.fighter: # let the figther component know who owns it
            self.fighter.owner = self
        self.ai = ai
        if self.ai: # let the AI component know who owns it
            self.ai.owner = self
        self.item = item
        if self.item: # let the item component know who owns it
            self.item.owner = self

    def move(self, dx, dy):
        if not is_blocked(self.x + dx, self.y + dy):
            # move by the given amount
            self.x += dx
            self.y += dy

    def draw(self):
        if libtcod.map_is_in_fov(fov_map, self.x, self.y) or (self.always_visible and map[self.x][self.y].explored):
            # set the color and then draw the character that represents this object at its position
            libtcod.console_set_foreground_color(con, self.color)
            libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)

    def clear(self):
        # erase the character that represents this object
        libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)

    def distance(self, x, y):
        # return the distance to some coordinates
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)

    def distance_to(self, other):
        # return the distance to another object
        return self.distance(other.x, other.y)

    def move_towards(self, target_x, target_y):
        # distance to the target
        distance = self.distance(target_x, target_y)

        # normalize vector from this object to the target to length 1
        # (preserving direction), then round it and convert to integer
        # so the movement is restricted to the map grid
        dx = int(round((target_x - self.x) / distance))
        dy = int(round((target_y - self.y) / distance))

        self.move(dx, dy)

    def send_to_back(self):
        # make this object be drawn first, so all others appear above it if they're in the same tile
        global objects

        objects.remove(self)
        objects.insert(0, self)

# Item that may be in inventory
class Item:
    def __init__(self, use_function=None):
        self.use_function = use_function

    # an item that can be picked up and used
    def pick_up(self):
        # add to the player's inventory and remove from the map
        if len(inventory) >= 26:
            message('Your inventory is full, cannot pick up ' + self.owner.name + '.', libtcod.red)
        else:
            inventory.append(self.owner)
            objects.remove(self.owner)
            message('You picked up a ' + self.owner.name + '!', libtcod.green)

    def drop(self):
        # add to the map and remove from the player's inventory. Also, place it at the player's coordinates
        objects.append(self.owner)
        inventory.remove(self.owner)
        self.owner.x = player.x
        self.owner.y = player.y
        message('You dropped a ' + self.owner.name + '.', libtcod.yellow)

    def use(self):
        # just call the "use_function" if it is defined
        if self.use_function is None:
            message('The ' + self.owner.name + ' cannot be used.')
        else:
            if self.use_function() != 'cancelled':
                inventory.remove(self.owner) # destroy after use, unless it was cancelled for some reason

# An object than can attack or be attacked
class Fighter:
    # combat-related properties and methods (monster, player, NPC)
    def __init__(self, hp, defense, power, xp, death_function=None):
        self.max_hp = hp
        self.hp = hp
        self.defense = defense
        self.power = power
        self.xp = xp
        self.death_function = death_function

    def take_damage(self, damage):
        global player

        # apply damage if possible
        if damage > 0:
            self.hp -= damage
        # check for death. If there's a death function, call it
        if self.hp <= 0:
            function = self.death_function
            if function is not None:
                function(self.owner)
        # yield experience to the player
        if self.owner != player:
            player.fighter.xp += self.xp

    def attack(self, target):
        # a simple formula for attack damage
        damage = self.power - target.fighter.defense

        if damage > 0:
            # make the target take some damage
            message(self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' hit points.')
            target.fighter.take_damage(damage)
        else:
            message(self.owner.name.capitalize() + ' attacks ' + target.name + ' but it has no effect!')

    def heal(self, amount):
        # heal by the given amount, without going over the maximum
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp

# Basic behaviour for any monster AI
class BasicMonster:
    # AI for a basic monster
    def take_turn(self):
        # a basic monster takes its turn. If you can see it, it can see you
        monster = self.owner
        if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
            # move towards player if far away
            if monster.distance_to(player) >= 2:
                monster.move_towards(player.x, player.y)
            # close enough, attack! (if the player is still alive)
            elif player.fighter.hp > 0:
                monster.fighter.attack(player)

# Confused monster AI
class ConfusedMonster:
    # AI for a temporaryly confused monster (reverts to previous AI after a while).
    def __init__(self, old_ai, num_turns=CONFUSE_NUM_TURNS):
        self.old_ai = old_ai
        self.num_turns = num_turns

    def take_turn(self):
        if self.num_turns > 0: # still confused...
            # move in a random direction, and decrease the number of turns confused
            self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
            self.num_turns -= 1

        else: # restore the previous AI (this one will be deleted because it's not referenced anymore)
            self.owner.ai = self.old_ai
            message('The ' + self.owner.name + ' is not longer confused!', libtcod.red)

# Example Dragon AI with state machine
class DragonAI:
    def __init__(self):
        self.state = 'chasing'

    def take_turn(self):
        if self.state == 'chasing':
            pass
        elif self.state == 'charing-fire-breath':
            pass

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

# GAME
#  Util
#   Choose one option from list of chances, returning its index
def random_choice_index(chances):
    # the dice will land on some number between 1 and the sum of the chances
    dice = libtcod.random_get_int(0, 1, sum(chances))

    # go through all chances, keeping the sum so far
    running_sum = 0
    choice = 0
    for w in chances:
        running_sum += w

        # see if the dice landed in the part that corresponds to this choice
        if dice <= running_sum:
            return choice
        choice += 1

#   Choose one option from dictionary of chances, returning its key
def random_choice(chances_dict):
    chances = chances_dict.values()
    strings = chances_dict.keys()

    return strings[random_choice_index(chances)]

#   Returns a value that depends on level. The table specifies what
#   value occurs after each level, default is 0.
def from_dungeon_level(table):
    global dungeon_level

    for (value, level) in reversed(table):
        if dungeon_level >= level:
            return value
    return 0

#  Fighters
#   Handle player death
def player_death(player):
    # the game ended!
    global game_state

    message('You died!', libtcod.red)
    game_state = 'dead'

    # for added effect, transform the player into a corpse!
    player.char = '%'
    player.color = libtcod.dark_red

#   Handle monster death
def monster_death(monster):
    # transform it into a nasty corpse! it doesn't block, can't be
    # attacked and doesn't move
    message('The ' + monster.name + ' is dead! You gain ' + str(monster.fighter.xp) + ' experience points.', libtcod.orange)
    monster.char = '%'
    monster.color = libtcod.dark_red
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = 'remains of ' + monster.name
    monster.send_to_back()

#   The player takes an action such as move or attack
def player_move_or_attack(dx, dy):
    global fov_recompute, player

    # the coordinates the player is moving to/attacking
    x = player.x + dx
    y = player.y + dy

    # try to find an attackable object there
    target = None
    for object in objects:
        if object.fighter and object.x == x and object.y == y:
            target = object
            break

    # attack if target found, move otherwise
    if target is not None:
        player.fighter.attack(target)
    else:
        player.move(dx, dy)
        fov_recompute = True

#  See if the player's experience is enough to level-up
def check_level_up():
    global player

    level_up_xp = LEVEL_UP_BASE + player.level * LEVEL_UP_FACTOR
    # it is! level up
    if player.fighter.xp >= level_up_xp:
        player.level += 1
        player.fighter.xp -= level_up_xp
        message('Your battle skills grow stronger! You reached level ' + str(player.level) + '!', libtcod.yellow)

        choice = None
        # keep asking until a choice is made
        while choice == None:
            choice = menu('Level up! Choose a stat to raise.\n',
                          ['Constitution (+20 HP from ' + str(player.fighter.max_hp) + ')',
                           'Strength (+1 attack, from ' + str(player.fighter.power) + ')',
                           'Agility (+1 defense, from ' + str(player.fighter.defense) + ')'],
                          LEVEL_SCREEN_WIDTH)

        if choice == 0:
            player.fighter.max_hp += 20
            player.fighter.hp += 20
        elif choice == 1:
            player.fighter.power += 1
        elif choice == 2:
            player.fighter.defense += 1

#  Items
#   Handle cast heal
def cast_heal():
    # heal the player
    if player.fighter.hp == player.fighter.max_hp:
        message('You are already at full health.', libtcod.red)
        return 'cancelled'

    message('Your wounds start to feel better!', libtcod.light_violet)
    player.fighter.heal(HEAL_AMOUNT)

#   Handle cast lightning bolt
def cast_lightning():
    # find closest enemy (inside a maximum range) and damage it
    monster = closest_monster(LIGHTNING_RANGE)
    if monster is None: # no enemy found within maximum range
        message('No enemy is close enough to strike.', libtcod.red)
        return 'cancelled'

    # zap it!
    message('A lightning bolt strikes the ' + monster.name + ' with a loud thunder! The damage is '
            + str(LIGHTNING_DAMAGE) + ' hit points.', libtcod.light_blue)
    monster.fighter.take_damage(LIGHTNING_DAMAGE)

#   Handle cast confusion
def cast_confuse():
    # ask the player for a target to confuse
    message('Left-click an enemy to confuse it, or right-click to cancel.', libtcod.light_cyan)
    monster = target_monster(CONFUSE_RANGE)
    if monster is None:
        message('Ok, not', libtcod.light_cyan)
        return 'cancelled'

    # replace the monster's AI with a "confused" one; after some turns it will restore the old AI
    old_ai = monster.ai
    monster.ai = ConfusedMonster(old_ai)
    monster.ai.owner = monster # tell the new component who owns it
    message('The eyes of the ' + monster.name + ' look vacant, as he starts to stumble around!', libtcod.light_green)

#   Handle cast fireball
def cast_fireball():
    # ask the player for a target tile to throw a fireball at
    message('Left-click a target tile for the fireball, or right-click to cancel.', libtcod.light_cyan)
    (x, y) = target_tile()
    if x is None:
        message('Ok, not', libtcod.light_cyan)
        return 'cancelled'
    message('The fireball explodes, burning everything within ' + str(FIREBALL_RADIUS) + ' tiles!', libtcod.orange)

    for obj in objects: # damage every fighter in range, including the player
        if obj.distance(x, y) <= FIREBALL_RADIUS and obj.fighter:
            message('The ' + obj.name + ' gets burnend for ' + str(FIREBALL_DAMAGE) + ' hit points.', libtcod.orange)
            obj.fighter.take_damage(FIREBALL_DAMAGE)

# MAP & OBJECTS
#  Test if tile is blocked
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

#  Which is the closest monster in sight?
def closest_monster(max_range):
    global fov_map
    
    # find closest enemy, up to a maximum range, and in the player's FOV
    closest_enemy = None
    closest_dist = max_range + 1 # start with (slightly more than) maximum range

    for object in objects:
        if object.fighter and not object == player and libtcod.map_is_in_fov(fov_map, object.x, object.y):
            # calculate distance between this object and the player
            dist = player.distance_to(object)
            if dist < closest_dist: # it's closer, so remember it
                closest_enemy = object
                closest_dist = dist

    return closest_enemy

#  Place objects in some room
def place_objects(room):
    global objects

    # maximum number of monsters per room
    max_monsters = from_dungeon_level([[2,1], [3,4], [5,6]])

    # chance for each monster
    monster_chances = {}
    monster_chances['orc'] = 80 # orc always shows up, even if all
                                # other monsters have 0 chance
    monster_chances['troll'] = from_dungeon_level([[15,3], [30,5], [60,7]])

    # maximum number of items per room
    max_items = from_dungeon_level([[1,1], [2,4]])

    # chance of each item (by default they have a chance of 0 at level
    # 1, which then goes up)
    item_chances = {}
    item_chances['heal'] = 35 # healing potion always shows up, even
                              # if all other items have 0 chance
    item_chances['lightning'] = from_dungeon_level([[25,4]])
    item_chances['fireball'] = from_dungeon_level([[25,6]])
    item_chances['confuse'] = from_dungeon_level([[10,2]])
    
    # choose random number of monsters
    num_monsters = libtcod.random_get_int(0, 0, max_monsters)

    for i in range(num_monsters):
        # choose random spot for this monster
        x = libtcod.random_get_int(0, room.x1 + 1, room.x2 - 1)
        y = libtcod.random_get_int(0, room.y1 + 1, room.y2 - 1)

        # only place it if the tile is not blocked
        if not is_blocked(x, y):
            choice = random_choice(monster_chances)
            if choice == 'orc':
                # create an orc
                fighter_component = Fighter(hp=20, defense=0, power=4, xp=35, death_function=monster_death)
                ai_component = BasicMonster()
                monster = Object(x, y, 'o', 'orc', libtcod.desaturated_green,
                                 blocks=True, fighter=fighter_component, ai=ai_component)
            elif choice == 'troll':
                # create a troll
                fighter_component = Fighter(hp=30, defense=2, power=8, xp=100, death_function=monster_death)
                ai_component = BasicMonster()
                monster = Object(x, y, 'T', 'troll', libtcod.darker_green,
                                 blocks=True, fighter=fighter_component, ai=ai_component)

            objects.append(monster)

    # choose random number of items
    num_items = libtcod.random_get_int(0, 0, max_items)

    for i in range(num_items):
        # choose random spot for this item
        x = libtcod.random_get_int(0, room.x1 + 1, room.x2 - 1)
        y = libtcod.random_get_int(0, room.y1 + 1, room.y2 - 1)

        # only place it if the tile is not blocked
        if not is_blocked(x, y):
            choice = random_choice(item_chances)
            if choice == 'heal': # healing potion
                # create a healing potion
                item_component = Item(use_function=cast_heal)
                item = Object(x, y, '!', 'healing potion', libtcod.violet, item=item_component)
            elif choice == 'lightning':
                # create a lightning bolt scroll
                item_component = Item(use_function=cast_lightning)
                item = Object(x, y, '#', 'scroll of lightning bolt', libtcod.light_yellow, item=item_component)
            elif choice == 'fireball':
                # create a fireball scroll
                item_component = Item(use_function=cast_fireball)
                item = Object(x, y, '#', 'scroll of fireball', libtcod.light_yellow, item=item_component)
            elif choice == 'confuse':
                # create a confuse scroll
                item_component = Item(use_function=cast_confuse)
                item = Object(x, y, '#', 'scroll of confusion', libtcod.light_yellow, item=item_component)

            objects.append(item)
            item.send_to_back() # items appear below all other objects

#  Create map
def make_map():
    global map, player, objects, stairs

    # fill map with "blocked" tiles
    map = [[ Tile(True)
        for y in range(MAP_HEIGHT) ]
            for x in range(MAP_WIDTH) ]

    # Objects Array
    # the list of objects with just the player
    objects = [player]

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

    # Create stairs at the center of the last room
    stairs = Object(new_x, new_y, '<', 'stairs', libtcod.white, always_visible=True)
    objects.insert(0, stairs)

#  Create a room in the map
def create_room(room):
    global map

    # go through the tiles in the rectangle and make them passable
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            map[x][y].blocked = False
            map[x][y].block_sight = False

#  Create horizontal tunnel
def create_h_tunnel(x1, x2, y):
    global map

    for x in range(min(x1, x2), max(x1, x2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False

#  Create vertical tunnel
def create_v_tunnel(y1, y2, x):
    global map

    for y in range(min(y1, y2), max(y1, y2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False

#  Advance to the next level
def next_level():
    global player, dungeon_level

    message('You take a moment to rest, and recover your strength.', libtcod.light_violet)
    player.fighter.heal(player.fighter.max_hp / 2) # heal the player by 50%

    message('After a rare moment of peace, you descend deeper into the heart of the dungeon...', libtcod.red)
    dungeon_level += 1
    make_map() # create a fresh new level
    initialize_fov()

# INPUT
#  Handle key input
def handle_keys():
    global game_state, player, stairs

#    key = libtcod.console_check_for_keypress() # real-time
    key = libtcod.console_check_for_keypress(libtcod.KEY_PRESSED) # turn-based

    if key.vk == libtcod.KEY_ENTER and key.lalt:
        # Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    elif key.vk == libtcod.KEY_ESCAPE:
        return 'exit' # exit game

    # movement keys
    if game_state == 'playing':
        if key.vk == libtcod.KEY_UP:
            player_move_or_attack(0, -1)
        elif key.vk == libtcod.KEY_DOWN:
            player_move_or_attack(0, 1)
        elif key.vk == libtcod.KEY_LEFT:
            player_move_or_attack(-1, 0)
        elif key.vk == libtcod.KEY_RIGHT:
            player_move_or_attack(1, 0)
        else:
            # test for other keys
            key_char = chr(key.c)

            if key_char == 'g':
                # pick up an item
                for object in objects: # look for an item in the player's tile
                    if object.x == player.x and object.y == player.y and object.item:
                        object.item.pick_up()
                        break
            if key_char == 'd':
                # show the inventory: if an item is selected, drop it
                chosen_item = inventory_menu('Press the key next to an item to drop it, or any other to cancel.\n')
                if chosen_item is not None:
                    chosen_item.drop()
            if key_char == 'i':
                # show the inventory
                chosen_item = inventory_menu('Press the key next to an item to use it, or any other to cancel.\n')
                if chosen_item is not None:
                    chosen_item.use()
            if key_char == '<':
                # go down stairs, if the player is on them
                if stairs.x == player.x and stairs.y == player.y:
                    next_level()
            if key_char == 'c':
                # show character information
                level_up_xp = LEVEL_UP_BASE + player.level * LEVEL_UP_FACTOR
                msgbox('Character Information\n\nLevel: ' + str(player.level) + '\nExperience: ' + str(player.fighter.xp) +
                       '\nExperience to level up: ' + str(level_up_xp) + '\n\nMaximum HP: ' + str(player.fighter.max_hp) +
                       '\nAttack: ' + str(player.fighter.power) + '\nDefense: ' + str(player.fighter.defense),
                       CHARACTER_SCREEN_WIDTH)

            return 'didnt-take-turn'

#  Mouse look command
def get_names_under_mouse():
    global fov_map
    
    # return a string with the names of all objects under the mouse
    mouse = libtcod.mouse_get_status()
    (x, y) = (mouse.cx, mouse.cy)

    # create list with names of all objects at the mouse's coordinates and in FOV
    names = [obj.name for obj in objects
             if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map, obj.x, obj.y)]

    names = ', '.join(names) # join the names, separated by commas
    return names.capitalize()

# Target tile with mouse
def target_tile(max_range=None):
    global fov_map
    
    # return the position of a tile left-clicked in player's FOV (optionally in a range), or (None,None) if right-clicked
    while True:
        # render the screen, this erases the inventory and shows the names of objects under the mouse
        render_all()
        libtcod.console_flush()

        key = libtcod.console_check_for_keypress()
        mouse = libtcod.mouse_get_status() # get mouse position and click status
        (x, y) = (mouse.cx, mouse.cy)

        if (mouse.lbutton_pressed and libtcod.map_is_in_fov(fov_map, x, y) and
            (max_range is None or player.distance(x, y) <= max_range)):
            return (x, y)

        if mouse.rbutton_pressed or key.vk == libtcod.KEY_ESCAPE:
            return (None, None) # cancel if the player right-clicked or pressed Escape

# Target a monster with the mouse
def target_monster(max_range=None):
    # returns a clicked monster inside FOV up to a range, or None if right-clicked
    while True:
        (x, y) = target_tile(max_range)
        if x is None: # player cancelled
            return None

        # return the first clicked monster, otherwise continue looping
        for obj in objects:
            if obj.x == x and obj.y == y and obj.fighter and obj != player:
                return obj

# RENDERING
#  Render status bar
def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
    global panel
    
    # render a bar (HP, experience, etc). First calculate the width of the bar
    bar_width = int(float(value) / maximum * total_width)

    # render the background first
    libtcod.console_set_background_color(panel, back_color)
    libtcod.console_rect(panel, x, y, total_width, 1, False)

    # now render the bar on top
    libtcod.console_set_background_color(panel, bar_color)
    if bar_width > 0:
        libtcod.console_rect(panel, x, y, bar_width, 1, False)

    # finally, some centered text with the values
    libtcod.console_set_foreground_color(panel, libtcod.white)
    libtcod.console_print_center(panel, x + total_width / 2, y, libtcod.BKGND_NONE,
                                 name + ': ' + str(value) + '/' + str(maximum))

#  Render all
def render_all():
    global color_light_wall, color_light_ground
    global color_dark_wall, color_dark_ground
    global fov_map, fov_recompute
    global player, map, dungeon_level, stairs

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

    # draw all objects in the list, except the player, we want it to
    # always appear over all the other objects! so it's drawn later.
    for object in objects:
        if object != player:
            object.draw()
    player.draw()

    # blit off-screen console to root one
    libtcod.console_blit(con, 0, 0, MAP_WIDTH, MAP_HEIGHT, 0, 0, 0)

    # prepare to render the GUI panel
    libtcod.console_set_background_color(panel, libtcod.black)
    libtcod.console_clear(panel)

    # print the game messages, one line at a time
    y = 1
    for (line, color) in game_msgs:
        libtcod.console_set_foreground_color(panel, color)
        libtcod.console_print_left(panel, MSG_X, y, libtcod.BKGND_NONE, line)
        y += 1

    # show the player's stats
    render_bar(1, 1, BAR_WIDTH, 'HP', player.fighter.hp, player.fighter.max_hp,
               libtcod.light_red, libtcod.dark_red)

    # dungeon level
    libtcod.console_print_left(panel, 1, 3, libtcod.BKGND_NONE, 'Dungeon level ' + str(dungeon_level))

    # mouse look command
    libtcod.console_set_foreground_color(panel, libtcod.light_gray)
    libtcod.console_print_left(panel, 1, 0, libtcod.BKGND_NONE, get_names_under_mouse())

    # blit the contents of "panel" to the root console
    libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)

# GUI
#  Add a message
def message(new_msg, color = libtcod.white):
    # split message if necessary, among multiple lines
    new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)

    for line in new_msg_lines:
        # if buffer is full, remove the first line to make room for the new one
        if len(game_msgs) == MSG_HEIGHT:
            del game_msgs[0]

        # add the new line as a tuple, with the text and the color
        game_msgs.append( (line, color) )

#  Displays a menu with selectable options
def menu(header, options, width):
    if len(options) > 26: raise ValueError('Cannot have a menu with more than 26 options.')

    # calculate the total height for the header (after auto-wrap) and one line per option
    header_height = libtcod.console_height_left_rect(con, 0, 0, width, SCREEN_HEIGHT, header)
    if header == '':
        header_height = 0
    height = len(options) + header_height

    # create an off-screen console that represents the menu's window
    window = libtcod.console_new(width, height)

    # print the header, with auto-wrap
    libtcod.console_set_foreground_color(window, libtcod.white)
    libtcod.console_print_left_rect(window, 0, 0, width, height, libtcod.BKGND_NONE, header)

    # print all the options
    y = header_height
    letter_index = ord('a')
    for option_text in options:
        text = '(' + chr(letter_index) + ') ' + option_text
        libtcod.console_print_left(window, 0, y, libtcod.BKGND_NONE, text)
        y += 1
        letter_index += 1

    # blit the contents of "window" to the root console
    x = SCREEN_WIDTH / 2 - width / 2
    y = SCREEN_HEIGHT / 2 - height / 2
    libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)

    # present the root console to the player and wait for a key-press
    libtcod.console_flush()
    key = libtcod.console_wait_for_keypress(True)

    if key.vk == libtcod.KEY_ENTER and key.lalt: # (special case) Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    # convert the ASCII code to an index; if it corresponds to an option, return it
    index = key.c - ord('a')
    if index >= 0 and index < len(options): return index
    return None

# Message box, a menu without options, just a message
def msgbox(text, width=50):
    menu(text, [], width) # use menu() as a sort of "message box"

#  Inventory menu
def inventory_menu(header):
    # show a menu with each item of the inventory as an option
    if len(inventory) == 0:
        options = ['Inventory is empty.']
    else:
        options = [item.name for item in inventory]

    index = menu(header, options, INVENTORY_WIDTH)
    # if an item was chosen, return it
    if index is None or len(inventory) == 0: return None
    return inventory[index].item

#  Main menu
def main_menu():
    img = libtcod.image_load('menu_background.png')

    while not libtcod.console_is_window_closed():
        # show the background image, at twice the regular console resolution
        libtcod.image_blit_2x(img, 0, 0, 0)

        # show the game's title, and some credits!
        libtcod.console_set_foreground_color(0, libtcod.light_yellow)
        libtcod.console_print_center(0, SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 6, libtcod.BKGND_NONE, 'TOMBS OF THE ANCIENT KINGS')
        libtcod.console_print_center(0, SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 4, libtcod.BKGND_NONE, 'By Jotaf')

        # show options and wait for the player's choice
        choice = menu('', ['Play a new game', 'Continue last game', 'Quit'], 24)

        if choice == 0: # new game
            new_game()
            play_game()
        elif choice == 1: # load last game
            try:
                load_game()
            except:
                msgbox('\n No saved game to load.\n', 24)
                continue
            play_game()
        elif choice == 2: # quit
            break

# MAIN MENU
#  New game
def new_game():
    global player, inventory, dungeon_level, game_msgs, game_state

    # Player init
    # create object representing the player
    fighter_component = Fighter(hp=100, defense=1, power=4, xp=0, death_function=player_death)
    player = Object(0, 0, '@', 'player', libtcod.white, blocks=True, fighter=fighter_component)
    player.level = 1

    # Map
    # dungeon level
    dungeon_level = 1
    # generate map (at this point it's not drawn to the screen)
    make_map()
    # FOV Map
    initialize_fov()

    # Game state
    game_state = 'playing'

    # Inventory
    inventory = []

    # Messages list
    # create the list of game messages and their colors, starts empty
    game_msgs = [] # tuples of (message str, color)

    # A warm welcoming message!
    message('Welcome stranger! Prepare to perish in the Tombs of the Ancient Kings.', libtcod.red)

#  Play game
def play_game():
    player_action = None

    #  Main loop
    while not libtcod.console_is_window_closed():
        # draw
        render_all()
        # flush data to screen
        libtcod.console_flush()

        # check level up
        check_level_up()

        # clear all objects
        for object in objects:
            object.clear()

        # handle keys and exit game if needed
        player_action = handle_keys()
        if player_action == 'exit':
            save_game()
            break

        # let monsters take their turn
        if game_state == 'playing' and player_action != 'didnt-take-turn':
            for object in objects:
                if object.ai:
                    object.ai.take_turn()

#  Save game
def save_game():
    global map, objects, player, inventory, game_msgs, game_state, dungeon_level, stairs

    # open a new empty shelve (possibly overwritting and old one) to write the game data
    file = shelve.open('savegame', 'n')
    file['map'] = map
    file['objects'] = objects
    file['player_index'] = objects.index(player) # index of player in objects list
    file['inventory'] = inventory
    file['game_msgs'] = game_msgs
    file['game_state'] = game_state
    file['stairs_index'] = objects.index(stairs)
    file['dungeon_level'] = dungeon_level
    file.close()

#  Load game
def load_game():
    # open the previously saved shelve and load the game data
    global map, objects, player, inventory, game_msgs, game_state, stairs, dungeon_level

    file = shelve.open('savegame', 'r')
    map = file['map']
    objects = file['objects']
    player = objects[file['player_index']] # get index of player in objects list and access it
    inventory = file['inventory']
    game_msgs = file['game_msgs']
    game_state = file['game_state']
    stairs = objects[file['stairs_index']]
    dungeon_level = file['dungeon_level']
    file.close()

    initialize_fov()

# INIT
#  FOV init
def initialize_fov():
    global fov_recompute, fov_map, map

    fov_recompute = True

    libtcod.console_clear(con) # unexplored areas start black (which is the default background color)

    # create the FOV map, according to the generated map
    fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)


# ---
# INITS
# ---
#  init font
libtcod.console_set_custom_font('arial12x12.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
#  for real-time RL and for mouse integration in turn-based RL
libtcod.sys_set_fps(LIMIT_FPS)
#  init root screen
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'python/libtcod tutorial', False)

#  Consoles
#   Off-screen main console
con = libtcod.console_new(MAP_WIDTH, MAP_HEIGHT)
#   Bottom panel
panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)


# ---
# MAIN
# ---
main_menu()
