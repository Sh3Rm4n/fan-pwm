#!/usr/bin/env python3

import logging
import os
import time
from pathlib import Path
from threading import Thread
from typing import NoReturn

import click
import xdg
from daemonize import Daemonize
from gpiozero import CPUTemperature, DigitalInputDevice, PWMOutputDevice
from gpiozero.pins.pigpio import PiGPIOFactory

MODULE_NAME = "fan-pwm"

RPM_LOGGING_S = 60
SPEED_UPDATE_TIME_S = 15


class Pwm:
    def __init__(self, pwm: Path):
        if not pwm.is_dir():
            AttributeError(
                f"'{pwm}' is not a dircetory and possibly not available",
            )
        self._pwm = pwm
        self._options = pwm / "pwm0"

    def __enter__(self):
        self.export()
        pass

    @property
    def duty_cycle(self):
        with self._options.joinpath("duty_cycle").open("r") as f:
            return int(f.readline().split("\n")[0])

    @duty_cycle.setter
    def duty_cycle(self, ns: int):
        with self._options.joinpath("duty_cycle").open("w") as f:
            f.write(f"{int(ns)}\n")

    @property
    def enable(self):
        with self._options.joinpath("enable").open("r") as f:
            return "1" in f.readline()

    @enable.setter
    def enable(self, b: bool):
        with self._options.joinpath("enable").open("w") as f:
            if b:
                f.write("1\n")
            else:
                f.write("0\n")

    @property
    def period(self):
        with self._options.joinpath("period").open("r") as f:
            return int(f.readline().split("\n")[0])

    @period.setter
    def period(self, ns: int):
        with self._options.joinpath("period").open("w") as f:
            f.write(f"{int(ns)}\n")

    def export(self):
        with self._pwm.joinpath("export").open("w") as pwm:
            pwm.write("0\n")
        while not self._options.exists():
            pass
        exit = False
        while not exit:
            try:
                while not self._options.joinpath("enable").open("w"):
                    pass
            except PermissionError:
                pass
            else:
                exit = True

    def unexport(self):
        if self._options.exists():
            with self._pwm.joinpath("unexport").open("w") as pwm:
                pwm.write("0\n")
            while self._options.exists():
                pass

    def __exit__(self, type, value, traceback):
        self.unexport()


def setup_log() -> list[int]:
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    logging.basicConfig(
        format="[%(levelname)s - %(asctime)s] - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    log_path = f"/var/log/{MODULE_NAME}.log"
    if not os.access(log_path, os.W_OK):
        log_path: Path = xdg.xdg_data_home() / MODULE_NAME
        log_path.mkdir(parents=True, exist_ok=True)
        log_path = log_path / f"{MODULE_NAME}.log"

    fh = logging.handlers.RotatingFileHandler(
        log_path,
        mode="a",
        maxBytes=1024**2,
        backupCount=2,
    )
    formatter = logging.Formatter(
        "[%(levelname)s - %(asctime)s] - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    fh.setFormatter(formatter)
    fh.setLevel(logging.DEBUG)

    logger.addHandler(fh)
    return [fh.stream.fileno()]


# <1.0 audible
# <0.7 okay for loads
# <0.5 quasy no noise
# <0.3 silent
# ~0.1 minimum

# pwm = OutputDevice(18, active_high=False, initial_value=1)


# TODO Get CPU temp
# TODO use DMA hardware PWM
# https://gpiozero.readthedocs.io/en/stable/api_pins.html#module-gpiozero.pins.rpio


class Rpm(Thread):
    def __init__(self):
        Thread.__init__(self, daemon=True)
        factory = PiGPIOFactory()
        self.rpm_pin = DigitalInputDevice(
            17, active_state=False, pull_up=None, pin_factory=factory
        )

    def run(self):
        while True:
            counter = 0
            second = 0
            while second < 1:
                time_start = time.time()
                if self.rpm_pin.wait_for_active(timeout=1):
                    counter += 1
                    self.rpm_pin.wait_for_inactive(timeout=1)
                time_elapsed = time.time() - time_start
                second += time_elapsed
            rpm = counter * 60
            if int(time.monotonic() + 1) % RPM_LOGGING_S == 0:
                logging.info(f"RPM = {rpm}")


class FanTemp(Thread):
    def __init__(self):
        Thread.__init__(self, daemon=True)
        factory = PiGPIOFactory()
        self.pwm_pin = PWMOutputDevice(
            12,
            initial_value=0.2,
            active_high=False,
            frequency=40000,
            pin_factory=factory,
        )
        self.cpu_temp = CPUTemperature(min_temp=40, max_temp=60, threshold=60)
        # self.pwm_pin = Pwm(Path('/sys/class/pwm/pwmchip0'))
        # self.pwm_pin.unexport()
        # self.pwm_pin.export()
        # self.period = 50000  # ns
        # self.pwm_pin.enable = False
        # self.pwm_pin.duty_cycle = 0
        # self.pwm_pin.period = self.period
        # self.pwm_pin.duty_cycle = 0.2 * self.period
        # self.pwm_pin.enable = True

    def run(self):
        temp_average = 0
        while True:
            time.sleep(1)
            timestamp = int(time.monotonic())
            # adjust speed every 15 seconds
            if timestamp % SPEED_UPDATE_TIME_S == 0:
                # make an average over the last 2 seconds
                steps = 50
                temp = 0
                for _ in range(steps):
                    time.sleep(2 / steps)
                    cpu_temp_value = self.cpu_temp.value
                    if cpu_temp_value > 0:
                        temp += cpu_temp_value
                temp_average = temp / steps
                # self.pwm_pin.duty_cycle = self.period * (
                #     0 + (
                #         0.1  # minimal speed
                #         + temp_average / 2  # temperature impact
                #     )
                # )
                self.pwm_pin.value = (
                    # minimal speed  # temperature impact
                    0.1 + temp_average / 2
                )
            # print log every 60 seconds
            if timestamp % 60 == 0:
                logging.info(
                    f"Speed {temp_average * 100:3.2f}%"
                    f" Temperatur {self.cpu_temp.temperature:2.1f} deg Celsius"
                )
            # error every 10 seconds
            if timestamp % 10 == 0:
                if self.cpu_temp.is_active:
                    logging.warn(
                        f"Max temp of {self.cpu_temp.max_temp} reached!"
                    )


def pwm_thread() -> NoReturn:
    logging.info("Start Fan Controller")
    fan_thread = FanTemp()
    rpm_thread = Rpm()

    fan_thread.start()
    rpm_thread.start()

    fan_thread.join()
    rpm_thread.join()


@click.command()
@click.option(
    "--log",
    default="warn",
    help="Debug level",
    type=click.Choice(["debug", "info", "warn", "error", "critical", "fatal"]),
)
@click.option(
    "--daemonize",
    default=False,
    is_flag=True,
    help="Daemonize the process",
)
def main(log, daemonize):
    keep_fds = setup_log()

    logger = logging.getLogger()
    logger.setLevel(log.upper())
    if daemonize:
        logging.info("Daemonize Fan Controller")
        daemon = Daemonize(
            app=f"{MODULE_NAME}d",
            pid=f"/tmp/{MODULE_NAME}d.pid",
            action=pwm_thread,
            keep_fds=keep_fds,
        )
        daemon.start()
    else:
        pwm_thread()


if __name__ == "__main__":
    main()
