 #include <LoRa.h>

float PR_TRANSMIT = 0.6;

bool GO = 1;

struct tpayload {
  byte cr_t = 0;           //1
  uint32_t id = 0;         //4
  byte void_6 = 0;         //1
  byte void_7 = 0;         //1
  byte void_8 = 0;         //1
  byte void_9 = 0;         //1
  byte void_10 = 0;        //1
  byte void_11 = 0;        //1
  byte void_12 = 0;        //1
  byte void_13 = 0;        //1
  byte void_14 = 0;        //1
  byte void_15 = 0;        //1
  byte void_16 = 0;        //1
};

// CONFIGURATION PARAMETERS
int CONFIG = 3;
int       sf[] = {12,     11,     10,     9,      8,      7,      7};
long int  bw[] = {125000, 125000, 125000, 125000, 125000, 125000, 250000};
int CR = 0;
int interf_counter = 0;

int cr[4] = {5, 6, 7, 8};

// TIME VARIABLES
float rate = 0;
float sys_end;
float start_pkt;
float end_pkt;
float tr_pkt = 300; // just to initializem


void setup()
{
  Serial.begin(9600);
  while (!Serial);
  Serial.print("waiting for Confgs!");
  while (Serial.available() < 1);//just wait
  CONFIG = Serial.parseInt();

 while (Serial.available() < 1);//just wait
  CR = Serial.parseInt()-1;
  if(CR > 3){CR = 0;}
  
  while (Serial.available() < 1);//just wait
  float PR_TRANSMIT = Serial.parseFloat();

 int cr_ = CR+1;
   Serial.println("-_-_-_-_-_-_-_-_-_-_-_-  PARAMS  -_-_-_-_-_-_-_-_-_-_-_-");
   Serial.println("");
   Serial.println("CONFIG: " +(String)CONFIG + "  -->  SF: " +(String)sf[CONFIG] +" BW: " +(String)bw[CONFIG]);
   Serial.println("");
   Serial.println("CR: " +(String)cr_+"  -->  CR: " +(String)cr[CR]);
   Serial.println("");
   Serial.println("PR_TRANSMIT: " +(String)PR_TRANSMIT);
   Serial.println("");
   Serial.println("-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-");
   while(Serial.available() > 0) {
     char t = Serial.read();
   }
   
  
  if (!LoRa.begin(868000000)) {
    Serial.println("Starting LoRa failed!");
    while (1);
  }

  change_config();

  // Parameters always fixed:
  LoRa.setPreambleLength(8);
  LoRa.setTxPower(14);
  LoRa.setSyncWord(0x39);
  LoRa.disableCrc();
}

void loop()
{
  while (Serial.available() < 1) {
    if (GO) {
      operate();                 // Press Enter to change configuration
    }
  }
  while (Serial.available() > 0) {
    Serial.read();
  }
  check_state();
}

void check_state()
{
  if ((CONFIG == 7) && (CR == 4)) {
    sys_end = millis();
    Serial.println("########## Number of configurations exceeded ##########");
    Serial.println("\tSystem duration: " + (String)sys_end);
    Serial.println("\tTransmission time: " + (String)rate);

    rate = rate / sys_end;
    Serial.println("\tRate: " + (String)rate);
    while (true) {}
  }
  else {
    if (CR == 4) {
      CR = 0;
      change_config();
    }
    else {
      change_cr();
    }
  }
}

void change_config()
{
  LoRa.setSpreadingFactor(sf[CONFIG]);
  LoRa.setSignalBandwidth(bw[CONFIG]);
  LoRa.setCodingRate4(cr[CR]);

  Serial.println("\n\n######## Configuration changed into ########");
  Serial.println("\tSF " + (String)sf[CONFIG]);
  Serial.println("\tBW " + (String)bw[CONFIG]);
  Serial.println("\t\t\t\t\t\t######## CR changed into " + (String)cr[CR] + " ########");

  CONFIG = CONFIG + 1;
  CR = CR + 1;
  interf_counter = 0;
}

void change_cr()
{
  LoRa.setCodingRate4(cr[CR]);
  Serial.println("\t\t\t\t\t\t######## CR changed into " + (String)cr[CR] + " ########");
  
  CR = CR + 1;
}

void operate()
{
  float RND = random(0, 100) / 100.0;
  //Serial.print("Rndm value: " + (String)RND);

  
if (RND < PR_TRANSMIT) {
  
    tpayload pay;

    //////////////////////////////////////////////////
    start_pkt = millis();
    if (!LoRa.beginPacket()) {
      Serial.println("Radio is busy or on failure");
      return;
    }
    //for (int i=0; i<16; i++) {
    //LoRa.write((const uint8_t*)&pkt, 16);
    //}
    LoRa.write((const uint8_t*)&pay, sizeof(pay));
    LoRa.endPacket(false);
    end_pkt = millis();
    //////////////////////////////////////////////////

    tr_pkt = end_pkt - start_pkt;
    interf_counter  = interf_counter + 1;
    
    
    //Serial.println("\tTime to send: " + (String)tr_pkt + "interferenza numero: "+(String)interf_counter);
    rate = rate + tr_pkt;
  }
  else {
    //Serial.println(" ------");
    delay(tr_pkt);
  }
}
