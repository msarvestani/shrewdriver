
int PIN_PUFF = 11; //really 11, but 13 for now so light works

byte s = '0';

void setup(){
  pinMode(PIN_PUFF, OUTPUT);
  Serial.begin(57600);
}

void checkSerial(){
  if (Serial.available() > 0){
    s = Serial.read();
  
    if (s == '0'){
      //close valve, stopping airflow
      digitalWrite(PIN_PUFF, LOW);
    }
    else if (s == '1'){
      //open valve, allowing airflow
      digitalWrite(PIN_PUFF, HIGH);
    }
    else if (s == 'x'){
      //administer a puff
      digitalWrite(PIN_PUFF, HIGH);
      delay(100);
      digitalWrite(PIN_PUFF, LOW);
    }
    else if (s == '\n'){
      //terminator; do nothing
    }
    else if ((s == 'M') || (s == 'm')){
      //Signal to check device connection.
      //If computer sends Marco, device answers Polo.
      Serial.println("P");
    }
    else{
      Serial.print("Unrecognized command: '");
      Serial.print(char(s));
      Serial.println("'. Send 0 for closed or 1 for open.");
    }
  }
}

void loop(){
  checkSerial();  
}

