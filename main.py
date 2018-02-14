#import necessary modules we need to use, define the proper pins for led, motor, switch and I2C communication.
import time
import ujson
import ubinascii
import machine
import micropython
from machine import Pin, I2C
from umqtt.simple import MQTTClient
import ustruct as struct

# Default MQTT server to connect to
CLIENT_ID = "12345"
BROKER_ADDRESS = "192.168.0.10"

switch = machine.Pin(2, machine.Pin.IN)

led = machine.Pin(12)
pwmled = machine.PWM(led)
pwmled.freq(100000)

motor = machine.Pin(13)
pwmmotor = machine.PWM(motor)
pwmmotor.freq(250)

client = MQTTClient(CLIENT_ID, BROKER_ADDRESS)
i2c = I2C(scl=Pin(5), sda=Pin(4), freq=100000)

# Power up sensors
i2c.writeto_mem(0x39,0x0,bytearray([0x03]))
i2c.writeto_mem(0x29,0x0,bytearray([0x03]))

#----------------------------------------------------------------------------------
# Calculate lux from data gained by light sensor
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

    return lux

#----------------------------------------------------------------------------------
# Connect wifi until it is successful, print status
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
# Publish two luxs to MQTT broker
def publish(tulux):
    payload = ujson.dumps(tulux)
    print("payload: ", payload)
    TOPIC = b"HME"
    client.publish(TOPIC, payload)

#----------------------------------------------------------------------------------
def sub_cb(topic, msg):
    
    # Check control messages from the broker and do corresponding job
    if(msg == b"on"): # Turn on the light
        pwmled.duty(1023)
    elif(msg == b"off"): # Turn off the light
        pwmled.duty(0)
    elif(msg == b"fade"): # Turn off the light gradually
        dcyc = 500
        while(dcyc >= 0):
            pwmled.duty(dcyc)
            dcyc = dcyc - 100
            time.sleep_ms(600)

    # If there is no control message, motor will work as usual, Rotating to the direction of light
    else:
        tulux = ujson.loads(msg) # Load data from broker
        tudif = tulux[0] - tulux[1] # Calculate the difference of two luxs
        print("The difference is: ", tudif)
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

#----------------------------------------------------------------------------------
def main():
 
    wifi()
    client.set_callback(sub_cb)
    client.connect()
    client.subscribe(b"HME")
    s1_adr = 57 # Sensor1's Address
    s2_adr = 41 # Sensor2's Address
    i=-1 # To indicate switch mode
    
    while(True):
        lux1 = test(s1_adr) # Sensor1's Lux
        lux2 = test(s2_adr) # Sensor2's Lux
        lux_avg = (lux1 + lux2)*0.5 # Average Lux
        tulux = (lux1, lux2)
        publish(tulux)
        client.check_msg()
        
        # If the switch is being pressed, mode becomes 0, otherwise mode = 1
        mode = switch.value()
        
        if(mode == 0):
            i=i*(-1) # everytime the switch is pressed, we toggle i
        
        if(i>0):
            # If the switch is pressed an odd number of times
            # the light is switched to manual mode
            TOPIC = b"HME"
            client.check_msg()
        
        else:
            # Otherwise the light is in automatic mode
            # Being controlled according to Average Lux
            if(lux_avg <= 20):
                dutycircle = -50*int(lux_avg) + 1023
                pwmled.duty(dutycircle)
            else:
                pwmled.duty(0)
        
        time.sleep_ms(200)

if __name__ == "__main__":
    main()
