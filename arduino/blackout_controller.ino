// Blackout controller: Arduino + analog joystick + one mode/start button.
// VRx -> A0, VRy -> A1, SW -> D2, VCC/GND as marked on the joystick module.

const int X_PIN = A0;
const int Y_PIN = A1;
const int BUTTON_PIN = 2;
unsigned long lastMove = 0;
bool lastButton = HIGH;

void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  Serial.begin(115200);
}

void loop() {
  bool button = digitalRead(BUTTON_PIN);
  if (lastButton == HIGH && button == LOW) {
    Serial.println("START");
    delay(30);
  }
  lastButton = button;

  if (millis() - lastMove < 150) return;
  int x = analogRead(X_PIN);
  int y = analogRead(Y_PIN);
  const char* direction = nullptr;
  if (x < 300) direction = "L";
  else if (x > 700) direction = "R";
  else if (y < 300) direction = "U";
  else if (y > 700) direction = "D";

  if (direction) {
    // Hold the joystick button while moving to sneak.
    if (button == LOW) Serial.print("S");
    Serial.println(direction);
    lastMove = millis();
  }
}
