# Blackout Demo

Blackout is a 20-second building-scale survival game. The 17×9 tower is the game board, with the top row reserved for the power countdown.

## Run

From this directory:

```bash
python3 blackout_game.py
```

On macOS, you can instead double-click `Start Blackout.command` for a one-step launch. It starts the game server and opens the control console automatically.

Open `http://127.0.0.1:8765` in a browser. The app streams frames to the `calm-egret` simulator and plays synchronized audio through the Mac.

## Controls

- Arrow keys or WASD: sprint
- Shift plus direction: sneak
- Space or Enter: start
- Touch controls: use the on-screen arrows and Sneak mode checkbox

The simplified maze has 19 visible walls instead of 46. Walls appear as dim red cells, and the player's cool light progressively greys out within two cells of one. A blocked move brightens the attempted wall deep red. The hunter uses a brighter coral-red pulse, so the signals remain distinct.

Sprint movement is immediate and creates a large noise pulse that advances the hunter's next move. Three consecutive sprint steps trigger a two-cell hunter burst. Sneaking has a longer movement cooldown, emits much less noise, and breaks the sprint streak.

## Arduino controller

Upload `arduino/blackout_controller.ino` to an Arduino connected to an analog joystick:

- VRx to A0
- VRy to A1
- Joystick switch to D2
- VCC and GND as marked on the module

The game automatically searches `/dev/cu.usbmodem*` and `/dev/cu.usbserial*` at 115200 baud. Move the joystick to sprint. Hold its switch while moving to sneak. Press it while centered to start.

## Demo flow

1. The occupied building waits in attract mode.
2. Press Start.
3. Yellow office lights fail from top to bottom.
4. A red alarm scans the facade.
5. Green exit, white protagonist, and red hunter appear.
6. A large 3–2–1 countdown appears before the chase begins.
7. The player has 20 seconds to reach the exit.
8. Win, capture, and timeout have distinct endings.

The game returns to attract mode after each result; it never starts another round automatically.

## 60-second judge demo

1. Leave the building in its warm yellow attract state while you introduce the premise.
2. Say “the backup power has twenty seconds left,” then press Start.
3. Let the blackout cascade and red alarm play without touching the controls.
4. Point out the white player, red hunter, green exit, and horizontal power bar on the top floor.
5. Sprint for two steps, then sneak for one. Explain that the quiet step breaks the hunter's burst streak.
6. Reach the exit for the green recovery ending. Press Start again only if a judge wants to play.

Before presenting, keep both pages visible: the control console at `http://127.0.0.1:8765` and the tower at `https://sundai.willsarg.com/calm-egret?view=street`. Turn the Mac volume up and prevent it from sleeping.
