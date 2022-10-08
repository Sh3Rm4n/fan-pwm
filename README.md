# Software Fan PWM

Automatic speed control of a PWM compatible PC Fan via Raspberry Pi GPIO pins.

## About

This project contains a script increase the fan speed via PWM leveraging
[`gpiozero`]s [`PWMOutputDevice`] and changes the value of the speed according
to the CPU temperature

[`gpiozero`]: https://github.com/gpiozero/gpiozero
[`PWMOutputDevice`]: https://gpiozero.readthedocs.io/en/stable/api_output.html?highlight=PWMOutputDevice#pwmoutputdevice

It uses [`pigpio`] as the backend.

[`pigpio`]: https://abyz.me.uk/rpi/pigpio/pigpiod.html

(Version V79 is required to support the Raspberry Pi 4)

```bash
sudo apt install pigiod

sudo systemctl enable pigiod
```

This script may switch to the hardware based PWM using the `/sys/class/pwm/pwmchip0`
but I haven't got that to work for now.

## Hardware

Without a FAN this script is useless. Unfortunately a PWM capable FAN is not so
straight forward to attach to a Raspberry Pi.

I was able to find a 5 V PWM capable fan, which made it significantly easier than
using standard 12 V fans for PC cases.

The actual FAN I've settled on is a 140 mm 5 V Fan from Noctua, the
[NF-A14-PWM](https://noctua.at/en/nf-a14-pwm)

![140 mm NF Fan picture](https://noctua.at/pub/media/catalog/product/cache/0cdbea399f8ed06da39b3854134f6934/n/f/nf_a14_1_7.jpg)

Because the Raspberry Pi has only 3.3 V GPIOs which should not be connected with
5 V and is also not enough to properly drive the FAN. For that to work, I've
built a little adapter board inspired by this great [raspberry pi form post].

[raspberry pi form post]:https://forums.raspberrypi.com/viewtopic.php?t=244194#p1489766

![Schematic from the post](https://i.imgur.com/BMsqLfh.jpg)
