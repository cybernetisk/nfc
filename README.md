# nfc
NFC-system til Escape for bruk til bongsystem, internstatus, medlemsskap.

Mer informasjon ligger på den interne wikien til CYB:
https://confluence.cyb.no/x/FIBz

## Overordnet info

Raspberry Pi kommuniserer med NFC-leser og LCD-displays over I2C-protokollen.
For å støtte NFC-leseren må vi sette opp libnfc, se nedenfor.

Selve kjernen av systemet vil være et Python-script som kommuniserer med enhetene.
Kommunikasjon med LCD-displayene er ganske kurant å få til uten videre i Python ved bruk
av smbus-pakka (python-smbus). Dette gjør det enkelt å kommunisere over I2C og sende
data til displayene.

Kommunikasjon med NFC-chippen er en del mer komplisert. For dette har vi ikke funnet
noen god python-pakke, men vi hadde laget en tidligere prototype i C som benyttet
libnfc. Derfor har vi laget bindinger fra Python til C, slik at vi kan eksportere
funksjoner i C som bruker libnfc til Python. På denne måten kan vi lese fra NFC-chippen
i Python.


## Sette opp

### Nødvendige pakker på maskinen
Installeres med apt-get:
* i2c-tools
* python-smbus
* git-core

Tror også man trenger:
* cmake
* autoconf
* libtool
* python-dev

### Sette opp libnfc og i2c-støtte
For å kommunisere med NFC-chippen, benytter vi oss av [libnfc](https://github.com/nfc-tools/libnfc).

Last ned libnfc fra lenken ovenfor og følge oppskriften under.

NB! Dette er ikke testet slik det står her, så mulig det må noen tilpasninger til for at det skal funke.

```bash
# sørg for å være i mappen til libnfc som er lastet ned

sudo mkdir -p /etc/nfc/devices.d
sudo cp contrib/libnfc/pn532_i2c_on_rpi.conf.sample /etc/nfc/devices.d/pn532_i2c_on_rpi.conf

# aktiver i2c på raspberry pi

# i raspi-blacklist.conf, kommenter ut: #blacklist i2c-bcm2708
sudo vim /etc/modprobe.d/raspi-blacklist.conf

# edit /etc/modules, add new line: i2c-dev
sudo vim /etc/modules

# rediger filen, les kommentarene i den
sudo vim /etc/nfc/devices.d/pn532_i2c_on_rpi.conf

./configure --with-drivers pn532_i2c --sysconfdir=/etc --prefix=/usr

sudo make install

# nfc-biblioteket er nå tilgjengelig på maskinen
# vi må restarte for at i2c-støtten aktiveres
sudo shutdown -r 0

# gi tilgang til pi-brukeren til i2c
sudo adduser pi i2c

# sjekk for enheter
i2cdetect -y 1 # evt 0, se pn532_i2c_on_rpi.conf
nfc-list
```

Ved problemer med oppsett av I2C-portene, se [Using the I2C Interface](http://www.raspberry-projects.com/pi/programming-in-python/i2c-programming-in-python/using-the-i2c-interface-2).

### Kompilere Python-binding mot libnfc
Dette skal være ganske rett frem.

I hovedmappa til dette Git-repoet:

```bash
make
```

### Kjøre testen
```bash
python prototype.py
```

### Starte automatisk på Pi-en
For å få til dette kan man lage et enkelt init-script:

```bash
sudo vim /etc/init.d/cybnfc
```

Legg til innholdet:
```
case "$1" in
        start)
                python ~pi/nfc/prototype.py &
                ;;
esac
```

```bash
sudo chmod 755 /etc/init.d/cybnfc
sudo update-rc.d cybnfc defaults
```
