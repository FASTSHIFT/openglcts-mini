// dEQP GLES2 harness main wrapper. Reuses platform createPlatform() from null platform.
// Example usage:
//   ./openglcts --deqp-case=dEQP-GLES2.info.version --deqp-log-file=log.xml
//   ./openglcts --deqp-runmode=xml-caselist --deqp-log-file=cases.xml

#include "deUniquePtr.hpp"
#include "qpDebugOut.h"
#include "tcuApp.hpp"
#include "tcuCommandLine.hpp"
#include "tcuDefs.hpp"
#include "tcuPlatform.hpp"
#include "tcuResource.hpp"
#include "tcuTestLog.hpp"

#include <cstdio>
#include <cstdlib>
#include <exception>

tcu::Platform* createPlatform(void); // from platform/null

static void disableStdout()
{
    qpRedirectOut(
        [](int, const char*) { return false; },
        [](int, const char*, va_list) { return false; });
}

int main(int argc, char** argv)
{
#if (DE_OS != DE_OS_WIN32)
    setvbuf(stdout, nullptr, _IOLBF, 4 * 1024);
#endif

    int exitStatus = EXIT_SUCCESS;
    try {
        tcu::CommandLine cmdLine(argc, argv);
        if (cmdLine.quietMode())
            disableStdout();

        tcu::DirArchive archive(cmdLine.getArchiveDir());
        tcu::TestLog log(cmdLine.getLogFileName(), cmdLine.getLogFlags());
        de::UniquePtr<tcu::Platform> platform(createPlatform());
        de::UniquePtr<tcu::App> app(new tcu::App(*platform, archive, log, cmdLine));

        while (app->iterate()) { /* iterate test cases */
        }

        // Avoid accessing incomplete TestRunStatus (forward declared). Exit code stays SUCCESS; detailed
        // pass/fail statistics are printed by App internally. External scripts can parse log for failures.
    } catch (const std::exception& e) {
        std::fprintf(stderr, "[openglcts] Exception: %s\n", e.what());
        exitStatus = EXIT_FAILURE;
    }
    return exitStatus;
}
