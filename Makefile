all:
	gcc -Wall -Wextra -o nfc.so main.c -lnfc -shared -I/usr/include/python2.7
