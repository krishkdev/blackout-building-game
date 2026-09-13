#!/usr/bin/env python3
"""Blackout: a playable 9x17 building-scale chase game."""

from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock, Thread
import glob
import json
import math
import os
import random
import select
import subprocess
import time
import urllib.request


ROOT = Path(__file__).resolve().parent
AUDIO = ROOT / "audio"
DISPLAY_URL = "https://sundai.willsarg.com/api/i/calm-egret/frame"
HOST, PORT = "127.0.0.1", 8765
FPS = 8
ROUND_SECONDS = 20.0
ROWS, COLS = 17, 9

MAZE = (
    ".........",
    ".#...#...",
    ".........",
    "..#...#..",
    "....#....",
    ".#.....#.",
    ".........",
    "...#.#...",
    ".........",
    ".#..#..#.",
    ".........",
    "..#...#..",
    "....#....",
    ".#.....#.",
    "...#.#...",
    ".........",
)
WALKABLE = {(row + 1, col) for row, line in enumerate(MAZE) for col, cell in enumerate(line) if cell == "."}
START = (1, 0)
HUNTER_START = (1, 8)
EXIT = (16, 8)
DIRECTIONS = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}
WALLS = {(row, col) for row in range(1, ROWS) for col in range(COLS) if (row, col) not in WALKABLE}
WALL_COLOR = [38, 2, 7]
COUNTDOWN_DIGITS = {
    "3": ("11111", "00001", "00001", "01111", "00001", "00001", "11111"),
    "2": ("11111", "00001", "00001", "11111", "10000", "10000", "11111"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
}

_occupied_rng = random.Random(2026)
OCCUPIED = {(row, col) for row in range(ROWS) for col in range(COLS) if _occupied_rng.random() < 0.72}


def blank():
    return [[[0, 0, 2] for _ in range(COLS)] for _ in range(ROWS)]


def glow(frame, position, color, divisor=8):
    row, col = position
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        rr, cc = row + dr, col + dc
        if 0 <= rr < ROWS and 0 <= cc < COLS:
            frame[rr][cc] = [max(frame[rr][cc][i], color[i] // divisor) for i in range(3)]


def bfs_step(start, goal, blocked=frozenset()):
    queue = deque([start])
    previous = {start: None}
    while queue:
        current = queue.popleft()
        if current == goal:
            break
        for dr, dc in DIRECTIONS.values():
            nxt = (current[0] + dr, current[1] + dc)
            if nxt in WALKABLE and nxt not in blocked and nxt not in previous:
                previous[nxt] = current
                queue.append(nxt)
    if goal not in previous:
        return start
    cursor = goal
    while previous[cursor] not in (None, start):
        cursor = previous[cursor]
    return cursor


class Audio:
    def __init__(self):
        self.music = None
        self.effects = []

    def stop(self):
        processes = ([self.music] if self.music else []) + self.effects
        for process in processes:
            if process and process.poll() is None:
                process.terminate()
        self.music = None
        self.effects = []

    def play(self, filename, music=False):
        path = AUDIO / filename
        if not path.exists():
            return
        if music:
            self.stop()
        self.effects = [p for p in self.effects if p.poll() is None]
        process = subprocess.Popen(["/usr/bin/afplay", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if music:
            self.music = process
        else:
            self.effects.append(process)


class Game:
    def __init__(self):
        self.lock = Lock()
        self.audio = Audio()
        self.phase = "idle"
        self.phase_started = time.monotonic()
        self.round_started = None
        self.player = START
        self.hunter = HUNTER_START
        self.previous_hunter = HUNTER_START
        self.consumed = set()
        self.noise = 0.0
        self.noise_origin = START
        self.noise_started = -99.0
        self.next_player_move = 0.0
        self.next_hunter_move = 0.0
        self.next_heartbeat = 0.0
        self.sprint_streak = 0
        self.near_miss_until = -1.0
        self.blocked_until = -1.0
        self.blocked_position = None
        self.last_frame = blank()
        self.display_status = "connecting"
        self.controller = "keyboard / touch"
        self.outcome = None
        self._last_idle_second = -1

    def start(self):
        with self.lock:
            if self.phase not in ("idle", "won", "caught", "timeout"):
                return False
            self.reset_world()
            self.phase = "prologue"
            self.phase_started = time.monotonic()
            self.audio.play("prologue.wav", music=True)
            return True

    def reset_world(self):
        self.player = START
        self.hunter = HUNTER_START
        self.previous_hunter = HUNTER_START
        self.consumed = set()
        self.noise = 0.0
        self.noise_origin = START
        self.noise_started = -99.0
        self.outcome = None
        self.round_started = None
        self.sprint_streak = 0
        self.next_player_move = 0.0
        self.next_hunter_move = 0.0
        self.next_heartbeat = 0.0
        self.near_miss_until = -1.0
        self.blocked_until = -1.0
        self.blocked_position = None

    def begin_round(self, now):
        self.phase = "playing"
        self.phase_started = now
        self.round_started = now
        self.next_hunter_move = now + 0.9
        self.next_heartbeat = now
        self.audio.play("chase.wav", music=True)

    def move(self, direction, sneak=False):
        now = time.monotonic()
        with self.lock:
            if self.phase != "playing" or direction not in DIRECTIONS or now < self.next_player_move:
                return False
            dr, dc = DIRECTIONS[direction]
            target = (self.player[0] + dr, self.player[1] + dc)
            if target not in WALKABLE:
                self.blocked_until = now + 0.32
                self.blocked_position = target if 1 <= target[0] < ROWS and 0 <= target[1] < COLS else self.player
                return False
            old_distance = self.distance()
            self.player = target
            self.noise = 0.22 if sneak else 1.0
            self.noise_origin = target
            self.noise_started = now
            self.next_player_move = now + (0.52 if sneak else 0.16)
            if sneak:
                self.sprint_streak = 0
            else:
                self.sprint_streak += 1
                self.next_hunter_move -= 0.26
                # Three careless footsteps give the hunter a two-cell burst.
                if self.sprint_streak % 3 == 0:
                    for _ in range(2):
                        self.previous_hunter = self.hunter
                        self.hunter = bfs_step(self.hunter, self.player)
                        self.consumed.add(self.previous_hunter)
                        if self.hunter == self.player:
                            break
            new_distance = self.distance()
            if min(old_distance, new_distance) == 1 and new_distance > old_distance:
                self.near_miss_until = now + 0.25
                self.audio.play("near_miss.wav")
            self.check_outcome(now)
            return True

    def distance(self):
        return abs(self.player[0] - self.hunter[0]) + abs(self.player[1] - self.hunter[1])

    def remaining(self, now=None):
        now = now or time.monotonic()
        return ROUND_SECONDS if self.round_started is None else max(0.0, ROUND_SECONDS - (now - self.round_started))

    def check_outcome(self, now):
        if self.player == self.hunter:
            self.finish("caught", now)
        elif self.player == EXIT:
            self.finish("won", now)
        elif self.remaining(now) <= 0:
            self.finish("timeout", now)

    def finish(self, outcome, now):
        if self.phase != "playing":
            return
        self.phase = outcome
        self.outcome = outcome
        self.phase_started = now
        self.audio.play("win.wav" if outcome == "won" else "caught.wav", music=True)

    def update(self, now):
        with self.lock:
            if self.phase == "prologue" and now - self.phase_started >= 8.1:
                self.phase = "ready"
                self.phase_started = now
            elif self.phase == "ready" and now - self.phase_started >= 3.0:
                self.begin_round(now)
            elif self.phase == "playing":
                self.noise = max(0.0, self.noise - 0.055)
                if now >= self.next_hunter_move:
                    self.previous_hunter = self.hunter
                    self.hunter = bfs_step(self.hunter, self.player)
                    self.consumed.add(self.previous_hunter)
                    closeness = 1.0 - min(8, self.distance()) / 8
                    self.next_hunter_move = now + max(0.40, 0.92 - closeness * 0.30)
                if now >= self.next_heartbeat:
                    closeness = 1.0 - min(8, self.distance()) / 8
                    self.audio.play("heartbeat.wav")
                    self.next_heartbeat = now + max(0.30, 1.10 - closeness * 0.72)
                self.check_outcome(now)
            elif self.phase in ("won", "caught", "timeout") and now - self.phase_started >= 4.5:
                self.phase = "idle"
                self.phase_started = now
                self.audio.stop()
                self.reset_world()

    def timer(self, frame, remaining):
        segments = math.ceil((remaining / ROUND_SECONDS) * COLS)
        color = [170, 105, 0] if remaining > 10 else [235, 62, 0]
        if remaining <= 5:
            color = [255, 0, 3] if int(time.monotonic() * 8) % 2 == 0 else [62, 0, 1]
        for col in range(COLS):
            frame[0][col] = color[:] if col < segments else [3, 1, 0]

    def render_idle(self, now):
        frame = blank()
        tick = int(now * 2)
        rng = random.Random(4409 + tick)
        for row, col in OCCUPIED:
            warmth = rng.choice((105, 125, 145, 165))
            frame[row][col] = [warmth, int(warmth * 0.68), int(warmth * 0.16)]
        # A breathing white diamond is the start invitation.
        pulse = 125 + int(100 * (0.5 + 0.5 * math.sin(now * 3)))
        for position in ((7, 4), (8, 3), (8, 4), (8, 5), (9, 4)):
            frame[position[0]][position[1]] = [pulse, pulse, pulse]
        return frame

    def render_prologue(self, now):
        elapsed = now - self.phase_started
        if elapsed < 3.0:
            return self.render_idle(now)
        if elapsed < 5.7:
            dead_rows = min(ROWS, int(((elapsed - 3.0) / 2.7) * (ROWS + 1)))
            frame = blank()
            for row, col in OCCUPIED:
                if row >= dead_rows:
                    frame[row][col] = [145, 95, 22]
            if dead_rows < ROWS:
                frame[dead_rows] = [[100, 70, 20] for _ in range(COLS)]
            return frame
        frame = blank()
        if elapsed < 7.1:
            center = int(((elapsed - 5.7) / 1.4) * (ROWS - 1))
            for row in range(ROWS):
                strength = max(0, 245 - abs(row - center) * 100)
                if strength:
                    frame[row] = [[strength, 0, 2] for _ in range(COLS)]
        elif int(elapsed * 8) % 2 == 0:
            frame = [[[225, 0, 2] for _ in range(COLS)] for _ in range(ROWS)]
        return frame

    def render_ready(self, now):
        frame = blank()
        elapsed = now - self.phase_started
        stage = min(2, int(elapsed))
        for row, col in WALLS:
            frame[row][col] = WALL_COLOR[:]
        frame[EXIT[0]][EXIT[1]] = [0, 190, 30]
        frame[self.player[0]][self.player[1]] = [240, 250, 255]
        if stage >= 1:
            red = 120 + int(120 * (0.5 + 0.5 * math.sin(now * 8)))
            frame[self.hunter[0]][self.hunter[1]] = [red, red // 5, red // 8]
        digit = COUNTDOWN_DIGITS[str(3 - stage)]
        brightness = 195 + int(45 * (1 - elapsed % 1.0))
        for glyph_row, pixels in enumerate(digit):
            for glyph_col, lit in enumerate(pixels):
                if lit == "1":
                    frame[5 + glyph_row][2 + glyph_col] = [brightness, brightness, min(255, brightness + 10)]
        return frame

    def render_game(self, now):
        frame = blank()
        for row, col in WALLS:
            frame[row][col] = WALL_COLOR[:]
        nearest_wall = min(
            abs(row - self.player[0]) + abs(col - self.player[1])
            for row, col in WALLS
        )
        # The survivor's cool emergency light loses its color near solid walls.
        grey_amount = max(0.0, min(1.0, (3 - nearest_wall) / 2))
        for row, col in WALKABLE:
            distance = abs(row - self.player[0]) + abs(col - self.player[1])
            if distance <= 4 and (row, col) not in self.consumed:
                strength = max(3, 18 - distance * 4)
                cool = [strength // 3, strength, min(32, strength + 8)]
                grey = int(strength * 0.82)
                frame[row][col] = [
                    int(channel * (1 - grey_amount) + grey * grey_amount)
                    for channel in cool
                ]
        for row, col in self.consumed:
            frame[row][col] = [0, 0, 0]

        noise_age = now - self.noise_started
        if noise_age < 0.85:
            radius = max(1, int((noise_age / 0.85) * (6 if self.noise > 0.55 else 3)))
            brightness = int((35 + self.noise * 85) * (1 - noise_age / 0.85))
            for row, col in WALKABLE:
                if abs(row - self.noise_origin[0]) + abs(col - self.noise_origin[1]) == radius:
                    frame[row][col] = [brightness, brightness, min(255, brightness + 18)]

        remaining = self.remaining(now)
        if remaining <= 5 and (now - self.round_started) % 1.0 < 0.34:
            center = 1 + int((((now - self.round_started) % 1.0) / 0.34) * 15)
            for row in range(1, ROWS):
                warning = max(0, 70 - abs(row - center) * 30)
                for col in range(COLS):
                    frame[row][col][0] = max(frame[row][col][0], warning)

        frame[EXIT[0]][EXIT[1]] = [0, 180, 28]
        closeness = 1 - min(8, self.distance()) / 8
        beat_hz = 1 + closeness * 3.6
        red = int(90 + closeness * 90 + 75 * max(0, math.sin(now * beat_hz * math.tau)) ** 5)
        hunter_color = [min(255, red), min(54, red // 5), min(34, red // 8)]
        glow(frame, self.hunter, hunter_color, 6)
        frame[self.hunter[0]][self.hunter[1]] = hunter_color
        player_glow = [200, 230, 255] if grey_amount < 0.5 else [212, 212, 218]
        glow(frame, self.player, player_glow, 8)
        frame[self.player[0]][self.player[1]] = [240, 250, 255]

        # A rejected move briefly reveals the solid corridor wall in deep red.
        if now < self.blocked_until and self.blocked_position:
            row, col = self.blocked_position
            frame[row][col] = [92, 0, 10]

        if now < self.near_miss_until:
            amount = (self.near_miss_until - now) / 0.25
            for row in range(1, ROWS):
                for col in range(COLS):
                    frame[row][col] = [max(value, int(185 * amount)) for value in frame[row][col]]
        self.timer(frame, remaining)
        return frame

    def render_ending(self, now):
        progress = min(1.0, (now - self.phase_started) / 2.6)
        frame = blank()
        if self.phase == "won":
            lit_rows = max(1, int(progress * ROWS))
            for row in range(ROWS - lit_rows, ROWS):
                for col in range(COLS):
                    frame[row][col] = [0, 80 + int(140 * progress), 25]
            frame[EXIT[0]][EXIT[1]] = [230, 255, 235]
        elif self.phase == "caught":
            strength = 240 if int(progress * 18) % 2 == 0 else 18
            frame = [[[strength, 0, 2] for _ in range(COLS)] for _ in range(ROWS)]
        # Timeout is distinct: the timer dies, followed by absolute darkness.
        return frame

    def render(self, now):
        if self.phase == "idle":
            return self.render_idle(now)
        if self.phase == "prologue":
            return self.render_prologue(now)
        if self.phase == "ready":
            return self.render_ready(now)
        if self.phase == "playing":
            return self.render_game(now)
        return self.render_ending(now)

    def snapshot(self):
        with self.lock:
            now = time.monotonic()
            return {
                "phase": self.phase,
                "remaining": round(self.remaining(now), 1),
                "distance": self.distance(),
                "noise": round(self.noise, 2),
                "controller": self.controller,
                "display": self.display_status,
                "frame": self.last_frame,
            }


GAME = Game()


def display_loop():
    while True:
        started = time.monotonic()
        GAME.update(started)
        with GAME.lock:
            frame = GAME.render(started)
            GAME.last_frame = frame
        payload = json.dumps(frame, separators=(",", ":")).encode()
        request = urllib.request.Request(DISPLAY_URL, data=payload, headers={"Content-Type": "application/json", "User-Agent": "blackout-demo/1.0"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                GAME.display_status = "live" if response.status == 204 else f"HTTP {response.status}"
        except Exception:
            GAME.display_status = "reconnecting"
        time.sleep(max(0, 1 / FPS - (time.monotonic() - started)))


def serial_loop():
    """Read START/U/D/L/R and SU/SD/SL/SR from an Arduino without pyserial."""
    while True:
        devices = sorted(glob.glob("/dev/cu.usbmodem*") + glob.glob("/dev/cu.usbserial*"))
        if not devices:
            time.sleep(2)
            continue
        device = devices[0]
        try:
            subprocess.run(["stty", "-f", device, "115200", "raw", "-echo"], check=True, capture_output=True)
            descriptor = os.open(device, os.O_RDONLY | os.O_NONBLOCK)
            GAME.controller = Path(device).name
            buffer = b""
            while True:
                ready, _, _ = select.select([descriptor], [], [], 0.3)
                if not ready:
                    continue
                chunk = os.read(descriptor, 256)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    command = line.decode(errors="ignore").strip().upper()
                    if command == "START":
                        GAME.start()
                    else:
                        sneak = command.startswith("S")
                        key = command[-1:] if command else ""
                        direction = {"U": "up", "D": "down", "L": "left", "R": "right"}.get(key)
                        if direction:
                            GAME.move(direction, sneak)
        except Exception:
            pass
        finally:
            try:
                os.close(descriptor)
            except Exception:
                pass
            GAME.controller = "keyboard / touch"
        time.sleep(1)


class Handler(BaseHTTPRequestHandler):
    def send_json(self, value, status=200):
        data = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/state":
            self.send_json(GAME.snapshot())
            return
        if self.path in ("/", "/index.html"):
            data = (ROOT / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self.send_json({"ok": False, "error": "invalid JSON"}, 400)
            return
        if self.path == "/api/start":
            self.send_json({"ok": GAME.start()})
        elif self.path == "/api/move":
            self.send_json({"ok": GAME.move(body.get("direction", ""), bool(body.get("sneak")))})
        else:
            self.send_error(404)

    def log_message(self, *_):
        pass


def main():
    Thread(target=display_loop, daemon=True).start()
    Thread(target=serial_loop, daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Blackout control console: http://{HOST}:{PORT}", flush=True)
    print("Press Ctrl-C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        GAME.audio.stop()
        server.server_close()


if __name__ == "__main__":
    main()
