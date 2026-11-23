/* SMTV.app's main program (install/app/build.py builds it for arm64 and x86_64 in one file: clang -arch arm64 -arch x86_64).

   One SMTV.app for every Mac. It holds two Pythons, one per processor, in Contents/Resources/python-arm64 and
   python-x86_64, and starts the one native to this Mac. The processor is asked of the hardware (hw.optional.arm64):
   under Rosetta `uname` says x86_64 even on Apple silicon. Apple silicon takes arm64 from macOS 14 on (its libraries
   need 14); on macOS 13 it falls back to the Intel Python under Rosetta.

   Why a program and not a shell script: macOS cannot tell a script's processor and may treat the app as an Intel one
   (asking for Rosetta). A universal program is native on both.

   What it sets is what the Python needs to find its own files: PYTHONHOME, no user site, nothing from outside
   (PYTHONPATH…), a PATH with Homebrew and ~/.local/bin (an app from Finder gets a short one). What goes wrong before
   SMTV opens its own log lands in <SMTV_HOME or ~/.smtv>/logs/launch.log (one start's worth). Arguments from Finder are
   never passed on. SMTV_LAUNCHER_DRY=1 prints the Python it would start and exits (the build's check). */
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <mach-o/dyld.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include <unistd.h>

static int apple_silicon(void) {
    int arm = 0;
    size_t size = sizeof arm;
    return sysctlbyname("hw.optional.arm64", &arm, &size, NULL, 0) == 0 && arm == 1;
}

static int macos_major(void) {
    char v[32] = {0};
    size_t size = sizeof v - 1;
    return sysctlbyname("kern.osproductversion", v, &size, NULL, 0) == 0 ? atoi(v) : 0;
}

static void open_log(void) {
    char dir[PATH_MAX], file[PATH_MAX];
    const char *home = getenv("HOME"), *smtv_home = getenv("SMTV_HOME");
    if (smtv_home && *smtv_home) snprintf(dir, sizeof dir, "%s", smtv_home);
    else snprintf(dir, sizeof dir, "%s/.smtv", home ? home : "/tmp");
    mkdir(dir, 0700);
    strncat(dir, "/logs", sizeof dir - strlen(dir) - 1);
    if (mkdir(dir, 0700) != 0 && errno != EEXIST) {
        const char *tmp = getenv("TMPDIR");
        snprintf(dir, sizeof dir, "%s", tmp && *tmp ? tmp : "/tmp");
    }
    snprintf(file, sizeof file, "%s/launch.log", dir);
    int fd = open(file, O_WRONLY | O_CREAT | O_TRUNC, 0600);
    if (fd >= 0) {
        dup2(fd, 1);
        dup2(fd, 2);
        close(fd);
    }
    int null = open("/dev/null", O_RDONLY);
    if (null >= 0) {
        dup2(null, 0);
        close(null);
    }
}

int main(void) {
    char exe[PATH_MAX], real[PATH_MAX], contents[PATH_MAX], home[PATH_MAX], python[PATH_MAX], path[8192];
    uint32_t size = sizeof exe;
    if (_NSGetExecutablePath(exe, &size) != 0 || !realpath(exe, real)) return 1;
    char *slash = strrchr(real, '/');                    /* …/Contents/MacOS/SMTV → …/Contents */
    if (!slash) return 1;
    *slash = 0;
    slash = strrchr(real, '/');
    if (!slash) return 1;
    *slash = 0;
    snprintf(contents, sizeof contents, "%s", real);

    const char *arch = apple_silicon() && macos_major() >= 14 ? "arm64" : "x86_64";
    snprintf(home, sizeof home, "%s/Resources/python-%s", contents, arch);
    snprintf(python, sizeof python, "%s/MacOS/smtv-python-%s", contents, arch);

    const char *dry = getenv("SMTV_LAUNCHER_DRY");
    if (dry && strcmp(dry, "1") == 0) {
        printf("%s %s\n", arch, python);
        return 0;
    }

    setenv("PYTHONHOME", home, 1);
    setenv("PYTHONNOUSERSITE", "1", 1);
    unsetenv("PYTHONPATH");
    unsetenv("PYTHONSTARTUP");
    unsetenv("PYTHONEXECUTABLE");
    unsetenv("__PYVENV_LAUNCHER__");
    const char *old = getenv("PATH"), *user = getenv("HOME");
    snprintf(path, sizeof path, "%s:/opt/homebrew/bin:/usr/local/bin:%s/.local/bin",
             old && *old ? old : "/usr/bin:/bin:/usr/sbin:/sbin", user ? user : "");
    setenv("PATH", path, 1);

    open_log();
    if (!user || chdir(user) != 0) fprintf(stderr, "SMTV: no home folder\n");
    char *args[] = {python, "-m", "smtv", "app", NULL};
    execv(python, args);
    fprintf(stderr, "SMTV: could not start %s: %s\n", python, strerror(errno));
    return 1;
}
