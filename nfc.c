#include <Python.h>

#include <stdlib.h>
#include <nfc/nfc.h>

nfc_device *pnd;
nfc_target nt;

// Allocate only a pointer to nfc_context
nfc_context *context;

static const char* get_hex(const uint8_t *bytes, const size_t size)
{
	static char hexstr[22];

	int i;
	for(i = 0; i < (int)size && i < 10; ++i)
		sprintf(hexstr+i*2, "%02x", bytes[i]);

	hexstr[i*2] = 0;

	return hexstr;
}

static PyObject * my_nfc_open() //PyObject *self, PyObject *args)
{
	// Initialize libnfc and set the nfc_context
	nfc_init(&context);
	if (context == NULL) {
		printf("Unable to init libnfc (malloc)\n");
		exit(EXIT_FAILURE);
	}

	// Open, using the first available NFC device which can be in order of selection:
	//   - default device specified using environment variable or
	//   - first specified device in libnfc.conf (/etc/nfc) or
	//   - first specified device in device-configuration directory (/etc/nfc/devices.d) or
	//   - first auto-detected (if feature is not disabled in libnfc.conf) device
	pnd = nfc_open(context, NULL);

	if (pnd == NULL) {
		printf("ERROR: %s\n", "Unable to open NFC device.");
		exit(EXIT_FAILURE);
	}
	// Set opened NFC device to initiator mode
	if (nfc_initiator_init(pnd) < 0) {
		nfc_perror(pnd, "nfc_initiator_init");
		exit(EXIT_FAILURE);
	}

	//printf("NFC reader: %s opened\n", nfc_device_get_name(pnd));
	return Py_BuildValue("");
}

static PyObject * my_nfc_getid() //PyObject *self, PyObject *args)
{
	// Poll for a ISO14443A (MIFARE) tag
	const nfc_modulation nmMifare = {
		.nmt = NMT_ISO14443A,
		.nbr = NBR_106,
	};

	int x = nfc_initiator_select_passive_target(pnd, nmMifare, NULL, 0, &nt);
	if (x > 0)
	{
		return Py_BuildValue("s", get_hex(nt.nti.nai.abtUid, nt.nti.nai.szUidLen));
	}

	return Py_BuildValue("");
}

static PyObject * my_nfc_close() //PyObject *self, PyObject *args)
{
	nfc_close(pnd);
	nfc_exit(context);
	return Py_BuildValue("");
}

static PyMethodDef nfc_methods[] = {
	{"open", my_nfc_open, METH_VARARGS, "Open NFC-handle."},
	{"getid", my_nfc_getid, METH_VARARGS, "Get ID from NFC-card."},
	{"close", my_nfc_close, METH_VARARGS, "Close NFC-handle."},
	{NULL, NULL, 0, NULL}
};

static struct PyModuleDef nfc_module = {
	PyModuleDef_HEAD_INIT,
	"nfc",        /* m_name */
	NULL,         /* m_doc */
	-1,           /* m_size */
	nfc_methods,  /* m_methods */
	NULL,         /* m_reload */
	NULL,         /* m_traverse */
	NULL,         /* m_clear */
	NULL          /* m_tree */
};

PyMODINIT_FUNC initnfc(void)
{
	return PyModule_Create(&nfc_module);
}

static wchar_t* char_to_wchar(const char* text)
{
	size_t size = strlen(text) + 1;
	wchar_t *wa = malloc(sizeof(wchar_t) * size);
	mbstowcs(wa, text, size);
	return wa;
}

int main(int argc, char *argv[])
{
	(void) argc;
	wchar_t *wargv0 = char_to_wchar(argv[0]);

	PyImport_AppendInittab("nfc", initnfc);
	Py_SetProgramName(wargv0);
	free(wargv0);

	Py_Initialize();
	initnfc();
	return 0;
}
