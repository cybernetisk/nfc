all:
	gcc -Wall -Wextra -o nfc.so nfc.c -lnfc -shared -I/usr/include/python2.7
