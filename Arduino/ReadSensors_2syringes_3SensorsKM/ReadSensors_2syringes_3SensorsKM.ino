#include <CapacitiveSensor.h>

/*
  Sensor Arduino
	
	Listens for inputs from lick sensor and tap sensor.
	Forwards those to PC.

*/

#include <CapacitiveSensor.h>

#define PIN_LICK_LEFT_SENSOR 2
#define PIN_CAPACITIVE_GROUND_LICK_LEFT 3

#define PIN_LICK_CENTER_SENSOR 5
#define PIN_CAPACITIVE_GROUND_LICK_CENTER 6

#define PIN_LICK_RIGHT_SENSOR 8
#define PIN_CAPACITIVE_GROUND_LICK_RIGHT 9

#define PIN_LICK_LEFT_NOTIFY 11
#define PIN_LICK_RIGHT_NOTIFY 12
#define PIN_LICK_CENTER_NOTIFY 13


#define LICK_RIGHT_ON HIGH
#define LICK_RIGHT_OFF LOW

#define LICK_LEFT_OFF HIGH
#define LICK_LEFT_ON LOW


#define LICK_CENTER_ON HIGH
#define LICK_CENTER_OFF LOW


bool lickrightState = LICK_RIGHT_OFF;
bool lickleftState = LICK_LEFT_OFF;
bool lickcenterState = LICK_CENTER_OFF;

// lower thresholds to make tap / lick more sensitive. 
//Somewhere between 100 and 1000 is typical.
int lickThreshold = 500;

//Speed-accuracy tradeoff. 50 is a good compromise point.
int numLickSamples = 50;


CapacitiveSensor csLickLeft = CapacitiveSensor(PIN_CAPACITIVE_GROUND_LICK_LEFT,PIN_LICK_LEFT_SENSOR);
CapacitiveSensor csLickRight = CapacitiveSensor(PIN_CAPACITIVE_GROUND_LICK_RIGHT,PIN_LICK_RIGHT_SENSOR);
CapacitiveSensor csLickCenter = CapacitiveSensor(PIN_CAPACITIVE_GROUND_LICK_CENTER,PIN_LICK_CENTER_SENSOR);

int lickLevels[] = {0, lickThreshold, lickThreshold*2, lickThreshold*4, lickThreshold*8};

void setup() {
  delay(200); //let arduino wake up properly
  Serial.begin(57600);
  Serial.println("Sensors ready.");

  //disable capacitive autocalibration (apparently does nothing)
  csLickLeft.set_CS_AutocaL_Millis(0xFF);
  csLickRight.set_CS_AutocaL_Millis(0xFF);
  csLickCenter.set_CS_AutocaL_Millis(0xFF);
  
	//pin setup
	pinMode(PIN_LICK_RIGHT_SENSOR, INPUT);
  pinMode(PIN_LICK_LEFT_SENSOR, INPUT);
  pinMode(PIN_LICK_CENTER_SENSOR, INPUT);
  
  pinMode(PIN_LICK_LEFT_NOTIFY, OUTPUT);
  pinMode(PIN_LICK_RIGHT_NOTIFY, OUTPUT);
  pinMode(PIN_LICK_CENTER_NOTIFY, OUTPUT);
  
  digitalWrite(PIN_LICK_LEFT_NOTIFY, LOW);
  digitalWrite(PIN_LICK_RIGHT_NOTIFY, LOW);
  digitalWrite(PIN_LICK_CENTER_NOTIFY, LOW);

}


void checkLickLeft(){
	long lickleftReading =  csLickLeft.capacitiveSensor(numLickSamples);
  int lickleftLevel = 0;
  for(int i = 4; i > 0; i--){
    if(lickleftReading > lickLevels[i]){
      lickleftLevel = i;
      break;
    }
  }
	if(lickleftState == LICK_LEFT_OFF && lickleftLevel > 0){
    lickleftState = LICK_LEFT_ON;
    digitalWrite(PIN_LICK_LEFT_NOTIFY, HIGH);
    Serial.print("LEFTLx");
    Serial.println(lickleftLevel);
	}
  else if(lickleftState == LICK_LEFT_ON && lickleftLevel == 0){
    lickleftState = LICK_LEFT_OFF;
    digitalWrite(PIN_LICK_LEFT_NOTIFY, LOW);
    Serial.println("LEFTLo");
  }
}


void checkLickRight(){
  long lickrightReading =  csLickRight.capacitiveSensor(numLickSamples);
  int lickrightLevel = 0;
  for(int i = 4; i > 0; i--){
    if(lickrightReading > lickLevels[i]){
      lickrightLevel = i;
      break;
    }
  }
  if(lickrightState == LICK_RIGHT_OFF && lickrightLevel > 0){
    lickrightState = LICK_RIGHT_ON;
    digitalWrite(PIN_LICK_RIGHT_NOTIFY, HIGH);
    Serial.print("RIGHTLx");
    Serial.println(lickrightLevel);
  }
  else if(lickrightState == LICK_RIGHT_ON && lickrightLevel == 0){
    lickrightState = LICK_RIGHT_OFF;
    digitalWrite(PIN_LICK_RIGHT_NOTIFY, LOW);
    Serial.println("RIGHTLo");
  }
}


void checkLickCenter(){
  long lickcenterReading =  csLickCenter.capacitiveSensor(numLickSamples);
  int lickcenterLevel = 0;
  for(int i = 4; i > 0; i--){
    if(lickcenterReading > lickLevels[i]){
      lickcenterLevel = i;
      break;
    }
  }
  if(lickcenterState == LICK_CENTER_OFF && lickcenterLevel > 0){
    lickcenterState = LICK_CENTER_ON;
    digitalWrite(PIN_LICK_CENTER_NOTIFY, HIGH);
    Serial.print("CENTERLx");
    Serial.println(lickcenterLevel);
  }
  else if(lickcenterState == LICK_CENTER_ON && lickcenterLevel == 0){
    lickcenterState = LICK_CENTER_OFF;
    digitalWrite(PIN_LICK_CENTER_NOTIFY, LOW);
    Serial.println("CENTERLo");
  }
}



void checkSerial(){
  if(Serial.available()){
    byte s = Serial.read();
    if((s == 'm') || (s == 'M')){
      //Signal to check device connection.
      //If computer sends Marco, device answers Polo.
          Serial.println('P');
    }
  }
}

// the loop routine runs over and over again forever:
void loop() {
	//Check sensors
	checkLickLeft();
	checkLickRight();
  checkLickCenter();
  //checkSerial();
}








