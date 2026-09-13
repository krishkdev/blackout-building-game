# Blackout Demo

Blackout is a 20-second building-scale survival game. The 17×9 tower is the game board, with the top row reserved for the power countdown.

## Run

From this directory:

```bash
python3 blackout_game.py
```

On macOS, you can instead double-click `Start Blackout.command` for a one-step launch. It starts the game server and opens the phone-style remote automatically.

Open `http://127.0.0.1:8765/controller` locally, or open `http://YOUR_COMPUTER_IP:8765/controller` from a phone on the same Wi-Fi. The app streams frames to the `calm-egret` simulator and plays synchronized audio through the host.

For the headless Raspberry Pi installation and phone swipe controller, follow [`PI_SETUP.md`](PI_SETUP.md). Once installed, the remote is available at `http://blackout.local:8765/controller` and no laptop display is required.

The included `Dockerfile` supports public cloud deployment on Maritime. The phone controller plays the synchronized soundtrack itself when the server has no physical audio output.

## Phone controls

- Press the red button: start
- Swipe: sprint
- Hold briefly, then swipe: sneak
- Short vibration: movement accepted
- Double vibration: blocked move

The simplified maze has 19 clearly visible amber walls instead of 46. The player's cool light progressively greys out within two cells of one. A blocked move briefly brightens the attempted wall. The hunter uses a pulsing coral-red light, so the signals remain distinct.

Sprint movement is immediate and creates a noise pulse that slightly advances the hunter's next move. Five consecutive sprint steps trigger one bonus hunter step. Sneaking has a longer movement cooldown, emits much less noise, and breaks the sprint streak. The hunter's normal step interval ranges from 1.45 seconds at distance to about 1.05 seconds nearby.

## Arduino controller

Upload `arduino/blackout_controller.ino` to an Arduino connected to an analog joystick:

- VRx to A0
- VRy to A1
- Joystick switch to D2
- VCC and GND as marked on the module

The game automatically searches `/dev/cu.usbmodem*` and `/dev/cu.usbserial*` at 115200 baud. Move the joystick to sprint. Hold its switch while moving to sneak. Press it while centered to start.

## Demo flow

1. A mostly dark 3 a.m. office tower waits with sparse amber windows while `BLACKOUT` scrolls vertically in cool blue-white light.
2. Press Start.
3. The marquee stops immediately and the remaining office lights fail from top to bottom.
4. A red alarm scans the facade.
5. Green exit, white protagonist, and red hunter appear.
6. A large 3–2–1 countdown appears before the chase begins.
7. The player has 20 seconds to reach the exit.
8. Win, capture, and timeout have distinct endings.

The game returns to attract mode after each result; it never starts another round automatically.
The sparse amber windows remain steady outside a dedicated dark center lane while the title marquee advances one floor per second. Pressing Start replaces it immediately with the 4.1-second power-failure sequence. On launch, the service first sends a brief black clearing frame so stale simulator pixels cannot leak into the new run.

## 60-second judge demo

1. Leave the building in its warm yellow attract state while you introduce the premise.
2. Say “the backup power has twenty seconds left,” then press Start.
3. Let the blackout cascade and red alarm play without touching the controls.
4. Point out the white player, red hunter, green exit, and horizontal power bar on the top floor.
5. Sprint for two steps, then sneak for one. Explain that the quiet step breaks the hunter's burst streak.
6. Reach the exit for the green recovery ending. Press Start again only if a judge wants to play.

Before presenting, open the phone remote and the tower at `https://sundai.willsarg.com/calm-egret?view=street`. Turn the host volume up and prevent it from sleeping. The removed desktop preview is not needed; the building is the game board.
