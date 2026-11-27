/* ClipIt.exe, the Windows app's own program (install/app/build.py builds it with MinGW and puts it at the top of the
   folder; the icon and the version come from the resource file build.py writes beside it).

   It is small on purpose and has no Python in it: it starts app\pythonw.exe (Python's windowless program, as the
   Python Software Foundation published it) and nothing else. Being built from this repository is what lets it be code
   signed; Python and every other bundled file stay as their authors publish them.

   - No arguments (a double click): starts `app\pythonw.exe -m smtv app` and ends at once, so the window's process is
     the only one left and the folder can be updated in place.
   - Arguments (a job, `-c`, `-m smtv.zipupdate`): handed to pythonw.exe as they are; waits for it and returns its exit
     code, with the same standard handles.
   - Python's DLLs and the ._pth sit beside this program, not beside app\pythonw.exe: the top folder goes to the
     front of PATH for the process it starts (and every one that process starts).
   - app\pythonw.exe missing (a ZIP not unpacked, a file removed by an antivirus): one plain message box.
   - SMTV_LAUNCH_CHECK=<file> (install/app/smoke.py) writes the command it would start into that file instead of
     starting it. */
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <strsafe.h>
#include <wchar.h>

#define PYTHON_REL L"\\app\\pythonw.exe"
#define DEFAULT_ARGS L"-m smtv app"

static void fail(const wchar_t *text) {
    MessageBoxW(NULL, text, L"Clip It!", MB_OK | MB_ICONERROR | MB_SETFOREGROUND);
}

/* The command line after the program's own name, as it was typed (quotes and all): "C:\a b\ClipIt.exe" -c "x y" */
static const wchar_t *after_program(const wchar_t *line) {
    const wchar_t *p = line;
    if (*p == L'"') {
        for (p++; *p && *p != L'"'; p++) {}
        if (*p) p++;
    } else {
        while (*p && *p != L' ' && *p != L'\t') p++;
    }
    while (*p == L' ' || *p == L'\t') p++;
    return p;
}

static void write_check(const wchar_t *file, const wchar_t *command) {
    HANDLE h = CreateFileW(file, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) return;
    char utf8[8192];
    int n = WideCharToMultiByte(CP_UTF8, 0, command, -1, utf8, (int)sizeof utf8, NULL, NULL);
    DWORD written;
    if (n > 1) WriteFile(h, utf8, (DWORD)(n - 1), &written, NULL);
    CloseHandle(h);
}

int WINAPI WinMain(HINSTANCE inst, HINSTANCE prev, LPSTR cmd, int show) {
    (void)inst; (void)prev; (void)cmd; (void)show;
    wchar_t top[MAX_PATH], python[MAX_PATH + 16], line[8192], check[MAX_PATH], path[32768], with_top[32768 + MAX_PATH + 1];

    DWORD n = GetModuleFileNameW(NULL, top, MAX_PATH);
    if (n == 0 || n >= MAX_PATH) { fail(L"Clip It! cannot find its own folder."); return 1; }
    wchar_t *slash = wcsrchr(top, L'\\');
    if (!slash) { fail(L"Clip It! cannot find its own folder."); return 1; }
    *slash = 0;                                          /* the folder this program is in */

    if (FAILED(StringCchPrintfW(python, sizeof python / sizeof *python, L"%ls" PYTHON_REL, top))) {
        fail(L"Clip It! cannot start: its folder's name is too long.");
        return 1;
    }
    if (GetFileAttributesW(python) == INVALID_FILE_ATTRIBUTES) {
        fail(L"Clip It! cannot start: its files are missing.\n\n"
             L"Unpack the whole ZIP (right click, Extract All), open the folder it made and start ClipIt.exe from there. "
             L"If you did, download Clip It! again: an antivirus may have removed a file.");
        return 1;
    }

    const wchar_t *rest = after_program(GetCommandLineW());
    int detach = *rest == 0;
    if (FAILED(StringCchPrintfW(line, sizeof line / sizeof *line, L"\"%ls\" %ls", python, detach ? DEFAULT_ARGS : rest))) {
        fail(L"Clip It! cannot start: the command is too long.");
        return 1;
    }

    DWORD c = GetEnvironmentVariableW(L"SMTV_LAUNCH_CHECK", check, MAX_PATH);
    if (c > 0 && c < MAX_PATH) { write_check(check, line); return 0; }

    DWORD len = GetEnvironmentVariableW(L"PATH", path, sizeof path / sizeof *path);
    if (len >= sizeof path / sizeof *path) len = 0;      /* too long to extend: the DLLs are then found beside the program */
    if (SUCCEEDED(StringCchPrintfW(with_top, sizeof with_top / sizeof *with_top, len ? L"%ls;%ls" : L"%ls", top, path)))
        SetEnvironmentVariableW(L"PATH", with_top);

    STARTUPINFOW si = { sizeof si };
    PROCESS_INFORMATION pi;
    if (!CreateProcessW(python, line, NULL, NULL, TRUE, 0, NULL, NULL, &si, &pi)) {
        fail(L"Clip It! cannot start. Windows or an antivirus did not let app\\pythonw.exe run.\n\n"
             L"Right click ClipIt.exe, Properties, and tick Unblock if you see it; otherwise download Clip It! again.");
        return 1;
    }
    DWORD code = 0;
    if (!detach) {
        WaitForSingleObject(pi.hProcess, INFINITE);
        GetExitCodeProcess(pi.hProcess, &code);
    }
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return (int)code;
}
