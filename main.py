import time
import ujson
import ubinascii
import machine
import micropython
from machine import RTC
rtc = RTC()
rtc.datetime((2018, 2, 13, 3, 15, 10, 45, 0))
from machine import Pin, I2C
from umqtt.simple import MQTTClient
import ustruct as struct
CLIENT_ID = "12345"
BROKER_ADDRESS = "192.168.0.10"

switch = machine.Pin(2, machine.Pin.IN)

led = machine.Pin(12)
pwmled = machine.PWM(led)
pwmled.freq(100000)

motor = machine.Pin(13)
pwmmotor = machine.PWM(motor)
pwmmotor.freq(250)

buzzer = machine.Pin(14)
pwmbuzzer = machine.PWM(buzzer)
pwmbuzzer.freq(50000)
#from machine import Pin, PWM
#tempo = 5
#tones = {
#    'c': 262,
#    'd': 294,
#    'e': 330,
#    'f': 349,
#    'g': 392,
#    'a': 440,
#    'b': 494,
#    'C': 523,
#    ' ': 0,
#}
#beeper = PWM(Pin(14, Pin.OUT), freq = 440, duty = 0)
#melody = 'cdefgabC'
#rhythm = [8, 8, 8, 8, 8, 8, 8, 8]

client = MQTTClient(CLIENT_ID, BROKER_ADDRESS)
i2c = I2C(scl=Pin(5), sda=Pin(4), freq=100000)
i2c.writeto_mem(0x39,0x0,bytearray([0x03]))
i2c.writeto_mem(0x29,0x0,bytearray([0x03]))
#----------------------------------------------------------------------------------
def test(address):
    channel0 = i2c.readfrom_mem(address,0xAC,2)
    ch0 = int.from_bytes(channel0,'little')
    channel1 = i2c.readfrom_mem(address,0xAE,2)
    ch1 = int.from_bytes(channel1,'little')

    ratio = ch1/ch0
    if 0< ratio<= 0.50:
        lux = 0.0304*ch0 - 0.062*ch0*(ratio**1.4)
    elif 0.5< ratio <=0.61:
        lux = 0.0224*ch0 - 0.031*ch1
    elif 0.61< ratio<=0.80:
        lux = 0.0128*ch0 - 0.0153*ch1
    elif 0.8< ratio <=1.30:
        lux = 0.00146*ch0 - 0.00112*ch1
    else : lux = 0

#   payload = ujson.dumps({'Flux': lux})
#   print("ch0 =", ch0," ch1 =", ch1," lux =", lux, " payload =", payload)
    return lux
#----------------------------------------------------------------------------------
def wifi():
    import network
    ap_if = network.WLAN(network.AP_IF)
    ap_if.active(False)
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    check = False
    while(check == False):
        sta_if.connect('EEERover','exhibition')
        time.sleep(3)
        check = sta_if.isconnected()
        print(check)
#----------------------------------------------------------------------------------
def publish(tulux):
    payload = ujson.dumps(tulux)
    print(payload)
    TOPIC = b"edhaomar"
#    client.publish(TOPIC, bytes(payload,'utf-8'))
    client.publish(TOPIC, payload)
#    time.sleep_ms(500)
    client.check_msg()
#----------------------------------------------------------------------------------
def sub_cb(topic, msg):
    if(msg == b"on"):
        pwmled.duty(1023)
    elif(msg == b"off"):
        pwmled.duty(0)
    else:
        tulux = ujson.loads(msg)
        tudif = tulux[0] - tulux[1]
        print(tudif)
        if(tudif > 10):
            pwmmotor.duty(256)
        elif(5 < tudif<= 10):
            pwmmotor.duty(320)
        elif(0 < tudif<= 5 ):
            pwmmotor.duty(380)
        elif(-5 < tudif<= 0):
            pwmmotor.duty(450)
        else:
            pwmmotor.duty(512)
#            print('debug2')
#----------------------------------------------------------------------------------
def main():
    wifi()
    client.set_callback(sub_cb)
    client.connect()
    client.subscribe(b"edhaomar")
    s1_adr = 57
    s2_adr = 41
    i=-1
    
    while(True):
        datetime = rtc.datetime()
        print(datetime)

#        if(datetime[6] == 0):
#            for tone, length in zip(melody, rhythm):
#                beeper.freq(tones[tone])
#                time.sleep(tempo/length)
#            beeper.deinit()
#            pwmbuzzer.duty(512)
#            time.sleep_ms(10)
#            pwmbuzzer.duty(512)
#            time.sleep_ms(10)
#            pwmbuzzer.duty(1023)
#            time.sleep_ms(10)
#            pwmbuzzer.duty(512)
#            time.sleep_ms(10)
#            pwmbuzzer.duty(0)

        lux1 = test(s1_adr)
        lux2 = test(s2_adr)
        lux_avg = (lux1 + lux2)*0.5
        tulux = (lux1, lux2)
        publish(tulux)

        mode = switch.value()
        if(mode == 0):
            i=i*(-1)
        
        if(i>0):
            TOPIC = b"edhaomar"
            client.check_msg()
        
        else:
            if(lux_avg <= 20):
                dutycircle = -50*int(lux_avg) + 1023
                pwmled.duty(dutycircle)
            else:
                pwmled.duty(0)
        
        time.sleep_ms(100)

if __name__ == "__main__":
    main()
