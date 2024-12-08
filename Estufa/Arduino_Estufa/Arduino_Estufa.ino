const int LED1 = 12;    
const int LED2 = 8;  
const int LED3 = 7;  
const int LED4 = 4; 
bool leituraUmidade;

int Vo;
float R1 = 10000;
float logR2, R2, T;
float c1 = 1.009249522e-03, c2 = 2.378405444e-04, c3 = 2.019202697e-07;

void setup() {
  pinMode(LED1, OUTPUT);    
  pinMode(LED2, OUTPUT);    
  pinMode(LED3, OUTPUT);
  pinMode(LED4, OUTPUT);

  pinMode(2, INPUT);

  Serial.begin(9600);

  digitalWrite(LED1, LOW);
  digitalWrite(LED2, LOW);
  digitalWrite(LED3, LOW);
  digitalWrite(LED4, LOW);
}

void loop() {
  int valorLDR = analogRead(A0);     
  leituraUmidade = digitalRead(2);  

  Vo = analogRead(A1);                
  R2 = R1 * (1023.0 / (float)Vo - 1.0);
  logR2 = log(R2);
  T = (1.0 / (c1 + c2*logR2 + c3*logR2*logR2*logR2));
  T = T - 273.15;


  if (Serial.available()) {   
    String command = Serial.readStringUntil('\n');
    command.trim(); 

    if (command == "toggleIrrigador_ON") {
      digitalWrite(LED1, HIGH); // Acende o LED1
    } else if (command == "toggleIrrigador_OFF") {
      digitalWrite(LED1, LOW); // Apaga o LED1
    } else if (command == "toggleLampada_ON") {
      digitalWrite(LED2, HIGH); // Acende o LED2
    } else if (command == "toggleLampada_OFF") {
      digitalWrite(LED2, LOW); // Apaga o LED2
    } else if (command == "toggleAquecedor_ON") {
      digitalWrite(LED3, HIGH); // Acende o LED3
    } else if (command == "toggleAquecedor_OFF") {
      digitalWrite(LED3, LOW); // Apaga o LED3
    } else if (command == "toggleRefrigerador_ON") {
      digitalWrite(LED4, HIGH); // Acende o LED4
    } else if (command == "toggleRefrigerador_OFF") {
      digitalWrite(LED4, LOW); // Apaga o LED4
    } 
  }

  Serial.print("LDR:");
  Serial.print(valorLDR);
  Serial.print(";UMIDADE:");
  Serial.print(leituraUmidade);
  Serial.print(";TEMPERATURA:");
  Serial.println(T); 
}
