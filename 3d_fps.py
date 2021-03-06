import curses
from math import sin, cos, pi, sqrt, atan, fabs

# import pydevd_pycharm
# pydevd_pycharm.settrace('localhost', port=5678, stdoutToServer=True, stderrToServer=True)


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self):
        return f'{self.__class__.__name__}(x:{self.x}, y:{self.y})'

    def __repr__(self):
        return str(self)


class Vector:
    """Класс математического вектора"""

    def __init__(self, point, direction=None, length=None, end_point=None):
        """
            Создать вектор из точки start_point.
            Задать вектор можно двумя способами: либо передав направление и длину, либо передав конечную точку
        """
        self.start_point = point

        if end_point:
            self.dx = end_point.x - point.x
            self.dy = end_point.y - point.y
            self.module = self._determine_module()

        else:
            direction = (direction * pi) / 180
            self.dx = cos(direction) * length
            self.dy = -sin(direction) * length
            self.module = length

    def _determine_module(self):
        return sqrt(self.dx ** 2 + self.dy ** 2)

    @property
    def end_point(self):
        return Point(self.start_point.x + self.dx, self.start_point.y + self.dy)

    @property
    def angle(self):
        if self.dx == 0:
            if self.dy >= 0:
                return 90
            else:
                return 270
        else:
            angle = atan(self.dy / self.dx) * (180 / pi)
            if self.dx < 0:
                angle += 180
        return angle

    def __str__(self):
        return 'vector([%.2f,%.2f],{%.2f,%.2f})' % (self.dx, self.dy, self.angle, self.module)

    def __repr__(self):
        return str(self)

    @property
    def length(self):
        return self.module


class Level:
    def __init__(self, width, height, content):
        self.width = width
        self.height = height
        self.map = content

    def get_row(self, row):
        assert 0 <= row < self.height, f'Row {row} out of level bounds (0, {self.height})'
        return self.map[row * self.width: (row + 1) * self.width]

    def point_is_present(self, point):
        return (0 <= point.x < self.width) and (0 <= point.y < self.height)

    def get_cell(self, point):
        assert self.point_is_present(point), f'{point} out of level bounds (0, 0, {self.width} {self.height})'
        return self.map[int(point.y) * self.width + int(point.x)]

    def check_cell(self, point, cell):
        return self.get_cell(point) == cell

    def is_wall(self, point):
        try:
            return self.check_cell(point, '#')
        except AssertionError:
            return True


class Player:
    def __init__(self, position, direction):
        self.position = position
        self._dir = direction

    @property
    def dir(self):
        return self._dir

    @dir.setter
    def dir(self, value):
        self._dir = value % 360

    @property
    def x(self):
        return self.position.x

    @x.setter
    def x(self, value):
        self.position.x = value

    @property
    def y(self):
        return self.position.y

    @y.setter
    def y(self, value):
        self.position.y = value

    def move_forward(self, distance):
        self.position = Vector(self.position, self.dir, distance).end_point

    def move_back(self, distance):
        self.position = Vector(self.position, self.dir, -distance).end_point

    def get_dir_arrow(self):
        arrow_number = (self.dir + 22.5) // 45
        return '→↗↑↖←↙↓↘→'[int(arrow_number)]


class Camera:
    def __init__(self, viewport_width, viewport_height, fov=60, depth=21.0):
        self.fov = fov      # Угол обзора
        self.depth = depth  # Максимальная дистанция обзора
        self.vp_width, self.vp_height = viewport_width, viewport_height
        self.distances = []
        self.edges = []

    def raycast(self, player, level):
        """
        Бросаем лучи.
        Разбиваем область видимости (fov) на количество участков, равное ширине экрана/вьюпорта.
        Направлением начала отсчёта будет направление взгляда игрока минус половина области видимости.
        И для каждой координаты x экрана/вьюпорта мы бросаем луч/вектор, последовательно увеличивая его длину.
        Если луч попадает в стену, то записываем длину луча (расстояние до стены) в список и переходим к следующему x.
        Если длина луча стала больше глубины прорисовки, а стену мы так и не нашли,
        то добавляем в список значение глубины прорисовки.
        """
        self.distances = []
        self.edges = []
        for x in range(0, self.vp_width):
            ray_angle = player.dir + (self.fov / 2) - (x / self.vp_width) * self.fov
            distance_to_wall = 0.0
            wall_hit = False
            while not wall_hit and distance_to_wall < self.depth:
                distance_to_wall += 0.1
                current_ray = Vector(player.position, ray_angle, distance_to_wall)
                test_point = current_ray.end_point
                # проверяем, не вышел ли вектор за карту
                if not level.point_is_present(test_point):
                    distance_to_wall = self.depth
                # проверяем, не упёрся ли вектор в стену
                elif level.is_wall(test_point):
                    wall_hit = True

                """
                Если нашли стену, то кидаем векторы до углов блока. 
                Выбираем два самых "котортких" вектора и считаем угол между брошеным лучом и каждым из этих векторов.
                Если угол меньше четверти градуса, то считаем, что в этой координате x находится грань блока.
                """
                if wall_hit:
                    edge_vectors = []
                    for block_x in range(0, 2):
                        for block_y in range(0, 2):
                            edge_pos = Point(int(test_point.x) + block_x, int(test_point.y) + block_y)
                            edge_vector = Vector(player.position, end_point=edge_pos)
                            edge_vectors.append(edge_vector)

                    edge_vectors.sort(key=lambda vector: vector.length)
                    if (fabs(current_ray.angle - edge_vectors[0].angle) < 0.25
                            or fabs(current_ray.angle - edge_vectors[1].angle) < 0.25):
                        self.edges.append(x)

            self.distances.append(distance_to_wall)

    def render_viewport(self, screen):
        for x in range(0, self.vp_width):
            # считаем высоту стены, которая зависит от расстояни до неё
            y_top = int((self.vp_height / 2) - (self.vp_height / self.distances[x]))
            y_bot = self.vp_height - y_top
            # если x в списке с гранями, то вместо стены будем рисовать эту грань
            if x in self.edges:
                wall_char = '|'
            # "красим" стену в зависимости от расстояния до неё
            elif self.distances[x] <= self.depth / 3:
                wall_char = '█'
            elif self.distances[x] < self.depth / 2:
                wall_char = '▓'
            elif self.distances[x] < self.depth / 1.5:
                wall_char = '▒'
            elif self.distances[x] < self.depth:
                wall_char = '░'
            else:
                wall_char = ' '

            for y in range(0, self.vp_height - 1):
                # рисуем потолок
                if y in range(0, y_top):
                    screen.addstr(y, x, ' ')

                # рисуем стену
                elif y in range(y_top, y_bot):
                    screen.addstr(y, x, wall_char)

                # рисуем пол. В зависимости от высоты от низа используем те или иные символы
                elif y >= y_bot:
                    floor_dist = 1 - (y - self.vp_height / 2) / (self.vp_height / 2)
                    if floor_dist < 0.25:
                        screen.addstr(y, x, '#')
                    elif floor_dist < 0.5:
                        screen.addstr(y, x, 'x')
                    elif floor_dist < 0.75:
                        screen.addstr(y, x, '~')
                    elif floor_dist < 0.9:
                        screen.addstr(y, x, '-')
                    else:
                        screen.addstr(y, x, ' ')


# карта уровня
map_height = 16
map_width = 25
lvl_map = ("#########################"
           "#.......................#"
           "#....#########..........#"
           "#............#..........#"
           "#............#..........#"
           "#............#..........#"
           "#............#####......#"
           "#....###................#"
           "#....###.....#......##..#"
           "#............#......##..#"
           "#............#..........#"
           "#............#..........#"
           "#........########.......#"
           "#.......................#"
           "#.......................#"
           "#########################").replace('.', ' ')


def draw_minimap(screen, position, player, level):
    for y in range(0, level.height):
        screen.addstr(y + position.y, position.x, level.get_row(y))
    screen.addstr(int(player.y) + position.y, int(player.x) + position.x, player.get_dir_arrow())


def main_game(screen):
    viewport_width = curses.COLS
    viewport_height = curses.LINES
    key = 0
    level = Level(map_width, map_height, lvl_map)
    player = Player(Point(22.0, 14.0), 90.0)
    camera = Camera(viewport_width, viewport_height)

    while True:  # игровой цикл
        if key == ord('w'):
            player.move_forward(1)
            # если упёрлись в стену, то откатываем шаг
            # TODO Дописать условие, при котором игрок не перепрыгнет через стену
            #  (проверка нахождения игрока за полем или перелёт через стену)
            if level.is_wall(player.position):
                player.move_back(1)
        elif key == ord('s'):
            player.move_back(1)
            # если упёрлись в стену, то откатываем шаг
            if level.is_wall(player.position):
                player.move_forward(1)
        elif key == ord('d'):
            player.dir -= 5
        elif key == ord('a'):
            player.dir += 5

        camera.raycast(player, level)
        camera.render_viewport(screen)

        draw_minimap(screen, Point(0, 1), player, level)
        screen.addstr(0, 0, f'x={player.x: 6.2f} y={player.y: 6.2f} dir={player.dir:>5}')
        key = screen.getch()


curses.wrapper(main_game)
