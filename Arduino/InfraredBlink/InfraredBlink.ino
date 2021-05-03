/*
 * Blinks an infrared LED in front of the camera.
 * Also, sends a trigger pulse to record when the blinks happened.
 * Goal is to allows coordination of video to triggers later on.
 * 
 * Two sets of blinks go,for example there will be a set of 3 blinks then a space 
 * then 2 blinks. There are 25 such combinations of blinks so you can be pretty sure
 * what kind you got.
 * 
 * Blink sets happen roughly once every 2 minutes, but the timing is 
 * somewhat irregular. This should also help if verification.
 * 
 * LED HIGH is off and LOW is on.
 * So the LED connects to +5V on one side and the signal pin on the other.
 */

int PIN_LED = 2;
int PIN_SIGNAL = 4;

void setup() {
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_SIGNAL, OUTPUT);
  randomSeed(analogRead(0));
  digitalWrite(PIN_LED, HIGH);
  digitalWrite(PIN_SIGNAL, LOW);
}

void flash(int times){
  for(int i = 0; i < times; i++){
    //
    digitalWrite(PIN_LED, LOW); //on
    digitalWrite(PIN_SIGNAL, HIGH);
    delay(100);
    digitalWrite(PIN_LED, HIGH); //off
    digitalWrite(PIN_SIGNAL, LOW);
    delay(300);
  }
}

void loop() {
  int nFlashesFirst = random(1,6); //1 to 5 flashes
  int nFlashesSecond = random(1,6); //1 to 5 flashes
  int delayBetweenFlashSets = 400;
  
  flash(nFlashesFirst);
  delay(delayBetweenFlashSets);
  flash(nFlashesSecond);
  
  long waitTimeMins = random(1,4); //1 to 3 minutes
  long waitTimeSeconds = random(0,11); //up to an extra 10 seconds of wait, random
  long waitTime = 1000*waitTimeMins*60;
  waitTime += 1000*waitTimeSeconds;
  delay(waitTime);
}
