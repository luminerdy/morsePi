from gpiozero import LED
from time import sleep

LED_GPIO = 27

led = LED(LED_GPIO)

print("LED test running on GPIO27.")
print("Press Ctrl+C to stop.")

try:
    while True:
        print("LED ON")
        led.on()
        sleep(0.5)

        print("LED OFF")
        led.off()
        sleep(0.5)

except KeyboardInterrupt:
    led.off()
    print("\nLED test stopped.")
