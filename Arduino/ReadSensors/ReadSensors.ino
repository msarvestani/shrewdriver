/*
  Sensor Arduino
	
	Listens for inputs from lick sensor and tap sensor.
	Forwards those to PC.

*/

#include <CapacitiveSensor.h>

#define PIN_LICK_SENSOR 2
#define PIN_CAPACITIVE_GROUND_LICK 3

#define PIN_TAP_SENSOR 8
#define PIN_CAPACITIVE_GROUND_TAP 9

#define PIN_LICK_NOTIFY 11
#define PIN_TAP_NOTIFY 12

#define TAP_ON HIGH
#define TAP_OFF LOW

#define LICK_OFF HIGH
#define LICK_ON LOW

bool tapState = TAP_OFF;
bool lickState = LICK_OFF;

// lower thresholds to make tap / lick more sensitive. 
//Somewhere between 100 and 1000 is typical.
int tapThreshold = 500;
int lickThreshold = 100;

//Speed-accuracy tradeoff. 50 is a good compromise point.
int numTapSamples = 50;
int numLickSamples = 50;


CapacitiveSensor csLick = CapacitiveSensor(PIN_CAPACITIVE_GROUND_LICK,PIN_LICK_SENSOR);
CapacitiveSensor csTap = CapacitiveSensor(PIN_CAPACITIVE_GROUND_TAP,PIN_TAP_SENSOR);

int lickLevels[] = {0, lickThreshold, lickThreshold*2, lickThreshold*4, lickThreshold*8};
int tapLevels[] = {0, tapThreshold, tapThreshold*2, tapThreshold*4, tapThreshold*8};

void setup() {
  delay(200); //let arduino wake up properly
  Serial.begin(57600);
  Serial.println("Sensors ready.");

  //disable capacitive autocalibration (apparently does nothing)
  csLick.set_CS_AutocaL_Millis(0xFF);
  csTap.set_CS_AutocaL_Millis(0xFF);
  
	//pin setup
	pinMode(PIN_TAP_SENSOR, INPUT);
  pinMode(PIN_LICK_SENSOR, INPUT);
  
  pinMode(PIN_LICK_NOTIFY, OUTPUT);
  pinMode(PIN_TAP_NOTIFY, OUTPUT);
  
  digitalWrite(PIN_LICK_NOTIFY, LOW);
  digitalWrite(PIN_TAP_NOTIFY, LOW);
}


void checkLick(){
	long lickReading =  csLick.capacitiveSensor(numLickSamples);
  int lickLevel = 0;
  for(int i = 4; i > 0; i--){
    if(lickReading > lickLevels[i]){
      lickLevel = i;
      break;
    }
  }
	if(lickState == LICK_OFF && lickLevel > 0){
    lickState = LICK_ON;
    digitalWrite(PIN_LICK_NOTIFY, HIGH);
    Serial.print("Lx");
    Serial.println(lickLevel);
	}
  else if(lickState == LICK_ON && lickLevel == 0){
    lickState = LICK_OFF;
    digitalWrite(PIN_LICK_NOTIFY, LOW);
    Serial.println("Lo");
  }
}

void checkTap(){
	long tapReading =  csTap.capacitiveSensor(numTapSamples);
  int tapLevel = 0;
  for(int i = 4; i > 0; i--){
    if(tapReading > tapLevels[i]){
      tapLevel = i;
      break;
    }
  }
	if(tapState == TAP_OFF && tapLevel > 0){
		tapState = TAP_ON;
    digitalWrite(PIN_TAP_NOTIFY, HIGH);
    Serial.print("Tx");
    Serial.println(tapLevel);
	}
	else if(tapState == TAP_ON && tapLevel == 0){
		tapState = TAP_OFF;
    digitalWrite(PIN_TAP_NOTIFY, LOW);
    Serial.println("To");
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
	checkLick();
	checkTap();
  //checkSerial();
}








