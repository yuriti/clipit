"""Windows shortcuts (.lnk) and the taskbar id, through Windows' own shell objects (ctypes, no PowerShell).

Why not PowerShell: with Smart App Control on, Windows PowerShell runs in Constrained Language Mode, where the
WScript.Shell object that makes shortcuts is not allowed; and only the shell objects can write the taskbar id
(System.AppUserModel.ID) into a shortcut. A shortcut and a window with the same id are one button on the taskbar, and a
pinned SMTV starts SMTV, not Python.

Every function here runs only on Windows; launcher.py calls them through `System`, so the tests use fakes.
"""
from __future__ import annotations

import ctypes
import sys
import uuid
from ctypes import POINTER, byref, c_int, c_uint16, c_uint32, c_ulong, c_void_p, c_wchar_p

assert sys.platform == "win32"       # Windows only (and mypy skips the rest elsewhere)

CLSID_SHELL_LINK = "00021401-0000-0000-C000-000000000046"
IID_SHELL_LINK_W = "000214F9-0000-0000-C000-000000000046"
IID_PERSIST_FILE = "0000010B-0000-0000-C000-000000000046"
IID_PROPERTY_STORE = "886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"
PKEY_APP_USER_MODEL_ID = ("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3", 5)
FOLDER_DESKTOP = "B4BFCC3A-DB2C-424C-B029-7FE99A87C641"
FOLDER_PROGRAMS = "A77F5D77-2E2B-44C3-A6A2-ABA601054A51"     # the Start menu's Programs of this person
CLSCTX_INPROC_SERVER = 1
VT_LPWSTR = 31
MAX_PATH = 32768

# the methods' places in each object's table (Windows SDK: ShObjIdl_core.h, ObjIdl.h, propsys.h)
QUERY_INTERFACE, RELEASE = 0, 2
LINK_SET_DESCRIPTION, LINK_SET_WORKING_DIRECTORY, LINK_GET_ARGUMENTS, LINK_SET_ARGUMENTS = 7, 9, 10, 11
LINK_SET_ICON_LOCATION, LINK_SET_PATH = 17, 20
FILE_LOAD, FILE_SAVE = 5, 6
STORE_SET_VALUE, STORE_COMMIT = 6, 7


class GUID(ctypes.Structure):
    _fields_ = [("data1", c_uint32), ("data2", c_uint16), ("data3", c_uint16), ("data4", ctypes.c_ubyte * 8)]


def guid(text: str) -> GUID:
    return GUID.from_buffer_copy(uuid.UUID(text).bytes_le)


class PROPERTYKEY(ctypes.Structure):
    _fields_ = [("fmtid", GUID), ("pid", c_uint32)]


class PROPVARIANT(ctypes.Structure):
    _fields_ = [("vt", c_uint16), ("reserved1", c_uint16), ("reserved2", c_uint16), ("reserved3", c_uint16),
                ("value", c_void_p), ("value2", c_void_p)]


def _method(obj: c_void_p, index: int, *argtypes, restype=ctypes.HRESULT):
    """Method `index` of a COM object: an HRESULT error raises OSError."""
    table = ctypes.cast(obj, POINTER(POINTER(c_void_p)))[0]
    return ctypes.WINFUNCTYPE(restype, c_void_p, *argtypes)(table[index])


def _call(obj: c_void_p, index: int, argtypes: tuple, *args):
    return _method(obj, index, *argtypes)(obj, *args)


def _query(obj: c_void_p, iid: str) -> c_void_p:
    out = c_void_p()
    _call(obj, QUERY_INTERFACE, (POINTER(GUID), POINTER(c_void_p)), byref(guid(iid)), byref(out))
    return out


def _release(*objs: c_void_p) -> None:
    for obj in objs:
        if obj:
            _method(obj, RELEASE, restype=c_ulong)(obj)


def _shell_link() -> c_void_p:
    ole32 = ctypes.windll.ole32
    ole32.CoInitialize(None)             # S_FALSE when this thread already has COM: fine either way
    ole32.CoCreateInstance.restype = ctypes.HRESULT
    link = c_void_p()
    ole32.CoCreateInstance(byref(guid(CLSID_SHELL_LINK)), None, CLSCTX_INPROC_SERVER, byref(guid(IID_SHELL_LINK_W)),
                           byref(link))
    return link


def save(path: str, target: str, arguments: str, workdir: str, icon: str, app_id: str, description: str) -> None:
    """Writes the shortcut `path` (replacing one there): `target arguments`, with the icon and the taskbar id."""
    link = _shell_link()
    store, file = c_void_p(), c_void_p()
    try:
        _call(link, LINK_SET_PATH, (c_wchar_p,), target)
        _call(link, LINK_SET_ARGUMENTS, (c_wchar_p,), arguments)
        _call(link, LINK_SET_WORKING_DIRECTORY, (c_wchar_p,), workdir)
        _call(link, LINK_SET_ICON_LOCATION, (c_wchar_p, c_int), icon, 0)
        _call(link, LINK_SET_DESCRIPTION, (c_wchar_p,), description)
        store = _query(link, IID_PROPERTY_STORE)
        text = ctypes.create_unicode_buffer(app_id)
        value = PROPVARIANT(vt=VT_LPWSTR, value=ctypes.addressof(text))
        key = PROPERTYKEY(guid(PKEY_APP_USER_MODEL_ID[0]), PKEY_APP_USER_MODEL_ID[1])
        _call(store, STORE_SET_VALUE, (POINTER(PROPERTYKEY), POINTER(PROPVARIANT)), byref(key), byref(value))
        _call(store, STORE_COMMIT, ())
        file = _query(link, IID_PERSIST_FILE)
        _call(file, FILE_SAVE, (c_wchar_p, c_int), path, 1)
    finally:
        _release(file, store, link)


def arguments(path: str) -> str:
    """What the shortcut `path` passes to its program."""
    link = _shell_link()
    file = c_void_p()
    try:
        file = _query(link, IID_PERSIST_FILE)
        _call(file, FILE_LOAD, (c_wchar_p, c_uint32), path, 0)
        out = ctypes.create_unicode_buffer(MAX_PATH)
        _call(link, LINK_GET_ARGUMENTS, (c_wchar_p, c_int), out, MAX_PATH)
        return out.value
    finally:
        _release(file, link)


def folders() -> list[str]:
    """This person's desktop and Start menu Programs folders, wherever Windows keeps them (OneDrive included)."""
    shell32, ole32 = ctypes.windll.shell32, ctypes.windll.ole32
    shell32.SHGetKnownFolderPath.restype = ctypes.HRESULT
    found = []
    for folder in (FOLDER_DESKTOP, FOLDER_PROGRAMS):
        out = c_wchar_p()
        shell32.SHGetKnownFolderPath(byref(guid(folder)), 0, None, byref(out))
        found.append(out.value or "")
        ole32.CoTaskMemFree(out)
    return found


FILE_ATTRIBUTE_HIDDEN = 2


def hide(path: str) -> None:
    """Gives the file Explorer's «hidden» mark (shown only with «Hidden items» ticked)."""
    kernel32 = ctypes.windll.kernel32
    attrs = kernel32.GetFileAttributesW(c_wchar_p(path))
    if attrs == 0xFFFFFFFF or not kernel32.SetFileAttributesW(c_wchar_p(path), attrs | FILE_ATTRIBUTE_HIDDEN):
        raise ctypes.WinError()


def set_app_id(app_id: str) -> None:
    """This process's taskbar id: its windows group under it, not under Python."""
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID.restype = ctypes.HRESULT
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(c_wchar_p(app_id))
