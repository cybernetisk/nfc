all:
	gcc -Wall -fPIC -Wextra -o nfc.so nfc.c -lnfc -shared -I/usr/include/python3.4
