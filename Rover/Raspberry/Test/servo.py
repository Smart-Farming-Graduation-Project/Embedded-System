import RPi.GPIO as GPIO
from time import sleep
import signal

RightLeftPin = 12     # PWM 0
UpDownPin = 13        # PWM 1

GPIO.setmode(GPIO.BCM)

GPIO.setup(RightLeftPin, GPIO.OUT)
GPIO.setup(UpDownPin, GPIO.OUT)

RightLeftServo = GPIO.PWM(RightLeftPin, 50)  
RightLeftServo.start(0)

UpDownServo = GPIO.PWM(UpDownPin, 50)
UpDownServo.start(0)

def set_angle(servo,angle):
    duty_cycle = angle / 18 + 2
    servo.ChangeDutyCycle(duty_cycle)
    sleep(0.5)
    servo.ChangeDutyCycle(0)

def signal_handler(signum, frame):
    print("\nCleaning up GPIO...")
    RightLeftServo.stop()
    UpDownServo.stop()
    GPIO.cleanup()
    exit()

# Set up signal handlers
signal.signal(signal.SIGINT, signal_handler)  # Catch Ctrl+C

while True:
    for angle in range(0,181,20):
        print("dfvd")
        set_angle(RightLeftServo, angle)
        set_angle(UpDownServo, angle)
        sleep(2)
