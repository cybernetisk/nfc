#!/bin/bash
if [ "id -u"  != "0" ]; then
    echo "Please run the script as root" 1>&2
    exit 1
fi

# Install dependencies
apt-get update
apt-get install i2c-tools python3-smbus git-core cmake autoconf libtool python-dev libnfc-bin

# Download config file for NFC
mkdir -p /etc/nfc/devices.d/
curl https://raw.githubusercontent.com/nfc-tools/libnfc/master/contrib/libnfc/pn532_i2c_on_rpi.conf.sample > /etc/nfc/devices.d/pn532_i2c_rpi.conf
# The I2C port in the config is wrong, so we change it.
echo $(/etc/nfc/devices.d/pn532_i2c_rpi.conf | sed "s/i2c-0/i2c-1/g") > /etc/nfc/devices.d/pn532_i2c_rpi.conf

# Make changes to configs to enable I2C
echo "$(cat /boot/config.txt | sed "s/#dtparam=i2c/dtparam=i2c/g")" > /boot/config.txt
echo "bcm2708.vc_i2c_override=1" > /boot/cmdline.txt

# Make the NFC binary
make all

echo "Reboot to finish the setup." 1>&2
