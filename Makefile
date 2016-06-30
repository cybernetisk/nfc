all:
	gcc -Wall -fPIC -Wextra -o src/nfc.so src/nfc.c -lnfc -shared -I/usr/include/python3.4
