// Controls a stepper motor via an LCD keypad shield.
// Accepts triggers and serial commands.

#include <LiquidCrystal.h>

/* -- Syringe Constants -- */
#define SYRINGE_VOLUME_ML 30.0
#define SYRINGE_BARREL_LENGTH_MM 80.0

#define THREADED_ROD_PITCH 1.25
#define STEPS_PER_REVOLUTION 200.0
#define MICROSTEPS_PER_STEP 16.0

#define SPEED_MICROSECONDS_DELAY 200 //longer delay = lower speed
#define SPEED_MICROSECONDS_DELAY_MANUAL 100 //Speed up when moving pump manually

long ustepsPerMM = MICROSTEPS_PER_STEP * STEPS_PER_REVOLUTION / THREADED_ROD_PITCH;
long ustepsPerML = (MICROSTEPS_PER_STEP * STEPS_PER_REVOLUTION * SYRINGE_BARREL_LENGTH_MM) / (SYRINGE_VOLUME_ML * THREADED_ROD_PITCH );

const int mLBolusStepsLength = 9;
float mLBolusSteps[9] = {0.001, 0.005, 0.010, 0.050, 0.100, 0.500, 1.000, 5.000, 10.000};

enum{PUSH,PULL}; //syringe movement direction

/* -- UI and Keypad Constants -- */
enum {KEY_SELECT, KEY_RIGHT, KEY_LEFT, KEY_DOWN, KEY_UP, KEY_NONE};
int NUM_KEYS = 6;

//Upper limits for each key
int keyCutoffs[] = {714, //select
              835, //right
              879, //left
              917, //down
              977, //up
              1024}; //max value of analogRead

/* -- Keypad states -- */
int adc_key_in;
int key = KEY_NONE;
enum{MAIN, BOLUS_MENU}; //UI states
int uiState = MAIN;

/* -- Pin definitions -- */
int motorDirPin = 2;
int motorStepPin = 3;

int triggerPin = A3;
int bigTriggerPin = A4;

/* -- Default Parameters -- */
float mLBolus = 0.500; //default bolus size
float mLBigBolus = 1.000; //default large bolus size
float mLUsed = 0.0;
int mLBolusStepIdx = 3; //0.05 mL increments at first
float mLBolusStep = mLBolusSteps[mLBolusStepIdx];

long stepperPos = 0; //in microsteps
char charBuf[16];

//key and debounce params
long lastKeyRepeatAt = 0;
long keyRepeatDelay = 400;
long keyDebounce = 125;
int prevKey = KEY_NONE;
int selectHoldCount = 0;

//triggering
int prevBigTrigger = HIGH;
int prevTrigger = HIGH;

//serial
String serialStr = "";
boolean serialStrReady = false;

/* -- Initialize libraries -- */
LiquidCrystal lcd(8, 13, 9, 4, 5, 6, 7);

void setup(){
  /* LCD setup */  
  lcd.begin(16, 2);
  lcd.clear();
  pinMode(10, OUTPUT); //disable backlight

  lcd.print("SyringePump v2.1");

  /* Triggering setup */
  pinMode(triggerPin, INPUT);
  pinMode(bigTriggerPin, INPUT);
  digitalWrite(triggerPin, HIGH); //enable pullup resistor
  digitalWrite(bigTriggerPin, HIGH); //enable pullup resistor
  
  /* Motor Setup */
  pinMode(motorStepPin, OUTPUT);
  pinMode(motorDirPin, OUTPUT);
  
  /* Serial setup */
  //Note that serial commands must be terminated with a newline
  //to be processed. Check this setting in your serial monitor if 
  //serial commands aren't doing anything.
  Serial.begin(57600); //Note that your serial connection must be set to 57600 to work!
}

void loop(){
  //check for LCD updates
  readKey();
  
  //check serial port for new commands
  readSerial();
  if(serialStrReady){
    processSerial();
  }
}

void readSerial(){
    //pulls in characters from serial port as they arrive
    //builds serialStr and sets ready flag when newline is found
    //will not read during command execution
    while (Serial.available() && ! serialStrReady) {
      char inChar = (char)Serial.read(); 
     
      if ((inChar == 'm') || (inChar == 'M')){
        //Signal to check device connection.
        //If computer sends Marco, device answers Polo.
        Serial.println('P');
        return;
      }
      
      if (inChar == '\n') {
        serialStrReady = true;
      } 
      else{
        serialStr += inChar;
      }
    }
}

void processSerial(){
  //process serial commands as they are read in
        int uLbolus = serialStr.toInt();
        mLBolus = (float)uLbolus / 1000.0;
        if(mLBolus < 0){
          mLBolus = -mLBolus;
        bolus(PULL, false);
        }
        else{
          bolus(PUSH, false);
        }
        serialStrReady = false;
  serialStr = "";
        updateScreen();
     
}

void bolus(int direction, bool isManual){
        //Move stepper. Will not return until stepper is done moving.        
 
 //change units to steps
  long steps = (mLBolus * ustepsPerML);
  if(direction == PUSH){
                digitalWrite(motorDirPin, HIGH);
    steps = mLBolus * ustepsPerML;
    mLUsed += mLBolus;
  }
  else if(direction == PULL){
                digitalWrite(motorDirPin, LOW);
    if((mLUsed-mLBolus) > 0){
      mLUsed -= mLBolus;
    }
    else{
      mLUsed = 0;
    }
  } 

      float usDelay = SPEED_MICROSECONDS_DELAY; //can go down to 20 or 30
      if(isManual)
        usDelay = SPEED_MICROSECONDS_DELAY_MANUAL; //goes much faster
    
      for(int i=0; i < steps; i++){ 
        digitalWrite(motorStepPin, HIGH); 
        delayMicroseconds(usDelay); 
    
        digitalWrite(motorStepPin, LOW); 
        delayMicroseconds(usDelay); 
      } 

}

void readKey(){
  //Some UI niceness here. 
        //When user holds down a key, it will repeat every so often (keyRepeatDelay).
        //But when user presses and releases a key, 
        //the key becomes responsive again after the shorter debounce period (keyDebounce).

  adc_key_in = analogRead(0);
  key = getKeyNum(adc_key_in); // convert into key press

  long currentTime = millis();
  long timeSinceLastPress = (currentTime-lastKeyRepeatAt);
  
  boolean processThisKey = false;
  if (prevKey == key && timeSinceLastPress > keyRepeatDelay){
    processThisKey = true;
  }
  if(prevKey == KEY_NONE && timeSinceLastPress > keyDebounce){
    processThisKey = true;
  }
  if(key == KEY_NONE){
    processThisKey = false;
  }  
  
  //holding the SELECT key will move the pump to position 0
  if (key == KEY_SELECT && prevKey == KEY_SELECT){
      selectHoldCount++;
      if(selectHoldCount > 15000){
          //reset position to 0 mL used
          double savedBolusSize = mLBolus;
          mLBolus = mLUsed;
          bolus(PULL, true);
          mLBolus = savedBolusSize;
          updateScreen();
      }
  }
  else{
     selectHoldCount = 0; 
  }
          
  prevKey = key;
  
  if(processThisKey){
    doKeyAction(key);
    lastKeyRepeatAt = currentTime;
  }
}

void doKeyAction(unsigned int key){
  if(key == KEY_NONE){
    return;
  }

  if(key == KEY_SELECT){
    if(uiState == MAIN){
      uiState = BOLUS_MENU;
    }
    else if(BOLUS_MENU){
      uiState = MAIN;
    }
  }

  if(uiState == MAIN){
    if(key == KEY_LEFT){
      bolus(PULL, true);
    }
    if(key == KEY_RIGHT){
      bolus(PUSH, true);
    }
    if(key == KEY_UP){
      mLBolus += mLBolusStep;
    }
    if(key == KEY_DOWN){
      if((mLBolus - mLBolusStep) > 0){
        mLBolus -= mLBolusStep;
      }
      else{
        mLBolus = 0;
      }
    }
  }
  else if(uiState == BOLUS_MENU){
    if(key == KEY_LEFT){
      //nothin'
    }
    if(key == KEY_RIGHT){
      //nothin'
    }
    if(key == KEY_UP){
      if(mLBolusStepIdx < mLBolusStepsLength-1){
        mLBolusStepIdx++;
        mLBolusStep = mLBolusSteps[mLBolusStepIdx];
      }
    }
    if(key == KEY_DOWN){
      if(mLBolusStepIdx > 0){
        mLBolusStepIdx -= 1;
        mLBolusStep = mLBolusSteps[mLBolusStepIdx];
      }
    }
  }

  updateScreen();
}

void updateScreen(){
  //build strings for upper and lower lines of screen
  String s1; //upper line
  String s2; //lower line
  
  if(uiState == MAIN){
    s1 = String("Used ") + decToString(mLUsed) + String(" mL");
    s2 = (String("Bolus ") + decToString(mLBolus) + String(" mL"));   
  }
  else if(uiState == BOLUS_MENU){
    s1 = String("Menu> BolusStep");
    s2 = decToString(mLBolusStep);
  }

  //do actual screen update
  lcd.clear();

  s2.toCharArray(charBuf, 16);
  lcd.setCursor(0, 1);  //line=2, x=0
  lcd.print(charBuf);
  
  s1.toCharArray(charBuf, 16);
  lcd.setCursor(0, 0);  //line=1, x=0
  lcd.print(charBuf);
}

int getKeyNum(int value){
  //given an analogRead value (0-1024), return key associated with that value.
  for(int i=0; i<NUM_KEYS; i++){
     if (value < keyCutoffs[i]){
        return i;
     }
  }
}

String decToString(float decNumber){
  //not a general use converter! Just good for the numbers we're working with here.
  int wholePart = decNumber; //truncate
  int decPart = round(abs(decNumber*1000)-abs(wholePart*1000)); //3 decimal places
        String strZeros = String("");
        if(decPart < 10){
          strZeros = String("00");
        }  
        else if(decPart < 100){
          strZeros = String("0");
        }
  return String(wholePart) + String('.') + strZeros + String(decPart);
}
