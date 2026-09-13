# Raspberry Pi 4 setup

Blackout runs headlessly on Raspberry Pi OS and uses a phone only as a swipe remote. The building remains the game display.

## What you need

- Raspberry Pi 4 and power supply
- microSD card with Raspberry Pi OS Lite (64-bit)
- Powered 3.5 mm or USB speaker
- Wi-Fi with internet access
- A phone on the same local network

## 1. Prepare Raspberry Pi OS

In Raspberry Pi Imager, choose Raspberry Pi OS Lite (64-bit). In its customization screen:

- Set the hostname to `blackout`
- Configure the event Wi-Fi network
- Create your username and password
- Enable SSH

Write the card, insert it, and boot the Pi. No monitor is required.

## 2. Connect over SSH

```bash
ssh YOUR_USERNAME@blackout.local
```

If `.local` discovery does not work, find the Pi's address in your router or hotspot client list and use `ssh YOUR_USERNAME@PI_ADDRESS`.

## 3. Install Blackout

```bash
sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/krishkdev/blackout-building-game.git
cd blackout-building-game
chmod +x deploy/install-pi.sh
./deploy/install-pi.sh
```

The installer adds the audio utilities, creates a system service, starts Blackout immediately, and configures it to restart automatically after every boot.

## 4. Test audio

Connect the powered speaker and run:

```bash
aplay audio/prologue.wav
```

If sound uses the wrong output, run `sudo raspi-config`, open the audio settings, and select the 3.5 mm or USB output. Then restart Blackout with `sudo systemctl restart blackout`.

## 5. Connect the phone

Put the phone on the same Wi-Fi and open:

```text
http://blackout.local:8765/controller
```

If that address does not resolve, obtain the Pi address with `hostname -I` and open `http://PI_ADDRESS:8765/controller`.

The phone remote uses these gestures:

- Press the red button to start
- Swipe to sprint one cell
- Hold for a moment, then swipe to sneak one cell
- A short vibration confirms movement
- A double vibration indicates a blocked wall

Add the page to the phone's home screen for a full-screen controller.

## Demo-day network warning

Some public Wi-Fi networks prevent devices from communicating with each other. Test the phone-to-Pi connection before presenting. The most reliable setup is Ethernet internet for the Pi plus a private Pi Wi-Fi hotspot for the phone. A phone hotspot can also work if it permits communication between the phone and connected clients.

## Operations

```bash
sudo systemctl status blackout
journalctl -u blackout -f
sudo systemctl restart blackout
sudo systemctl stop blackout
```

To install a new version:

```bash
cd ~/blackout-building-game
git pull
sudo systemctl restart blackout
```

The health check is available at `http://blackout.local:8765/api/health`.
