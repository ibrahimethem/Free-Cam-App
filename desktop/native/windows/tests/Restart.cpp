// Real local-pipe regression: a cached reader must recover after output toggles.
// NOSUB_TRANSPORT_TEST omits only MF device registration, never the transport.
#include "FrameReader.h"
#include <mferror.h>
#include <wrl/client.h>
#include <iostream>
#include <thread>
#include <stdexcept>
#include <chrono>

extern "C" int32_t nosub_camera_output_start();
extern "C" int32_t nosub_camera_output_send(const void*, int32_t);
extern "C" void nosub_camera_output_stop();
extern "C" void nosub_camera_output_shutdown();
extern "C" const wchar_t* nosub_camera_test_pipe();

static void Expect(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
static bool Read(SimpleFrameGenerator& reader, uint8_t expectedY) {
    std::vector<uint8_t> frame(NoSub::FrameBytes);
    // Allow a first connection or a stale disconnected pipe to retry, but never
    // reset/recreate the reader: it models a video app holding its original source.
    for (int attempt = 0; attempt < 8; ++attempt) {
        Expect(SUCCEEDED(reader.CreateFrame(frame.data(), DWORD(frame.size()), NoSub::Width, 0)), "Frame read failed");
        if (frame[0] == expectedY && frame[NoSub::Width * NoSub::Height / 2] == expectedY) return true;
    }
    return false;
}
int main() {
    bool com = false, mf = false;
    int result = 1;
    try {
        Expect(SUCCEEDED(CoInitializeEx(nullptr, COINIT_MULTITHREADED)), "COM initialization failed"); com = true;
        Expect(SUCCEEDED(MFStartup(MF_VERSION)), "MF initialization failed"); mf = true;
        Expect(nosub_camera_output_start() == 1, "Initial start failed");
        const std::wstring original = nosub_camera_test_pipe();
        Expect(NoSub::ValidPipeName(original), "Invalid session endpoint");
        SimpleFrameGenerator first, second;
        first.SetPipeName(original); second.SetPipeName(original);
        Microsoft::WRL::ComPtr<IMFMediaType> type;
        Expect(SUCCEEDED(MFCreateMediaType(&type)), "Media type creation failed");
        type->SetGUID(MF_MT_SUBTYPE, MFVideoFormat_NV12);
        MFSetAttributeSize(type.Get(), MF_MT_FRAME_SIZE, NoSub::Width, NoSub::Height);
        Expect(SUCCEEDED(first.Initialize(type.Get())) && SUCCEEDED(second.Initialize(type.Get())), "Reader init failed");
        std::vector<uint8_t> bgra(NoSub::BgraBytes, 255);
        for (int cycle = 0; cycle < 5; ++cycle) {
            // Start on a different caller thread each time. Native COM ownership
            // must not follow the Python frame worker that happens to enable it.
            int started = 0;
            std::thread enable([&] { started = nosub_camera_output_start(); }); enable.join();
            Expect(started == 1, "Re-enable failed");
            Expect(original == nosub_camera_test_pipe(), "Toggle replaced cached reader endpoint");
            Expect(Read(first, 16), "Re-enable leaked a previous frame");
            Expect(nosub_camera_output_send(bgra.data(), int32_t(bgra.size())) == 1, "Write failed");
            Expect(Read(first, 235) && Read(second, 235), "Cached reader stayed black after re-enable");
            // Re-send because reading both consumers may span a slow CI interval.
            nosub_camera_output_send(bgra.data(), int32_t(bgra.size()));
            std::this_thread::sleep_for(std::chrono::milliseconds(1100));
            Expect(Read(first, 16), "Stale frame did not turn black");
            nosub_camera_output_send(bgra.data(), int32_t(bgra.size()));
            Expect(Read(first, 235), "Reader did not recover from stale input");
            std::thread disable([] { nosub_camera_output_stop(); }); disable.join();
            Expect(Read(first, 16) && Read(second, 16), "Disabled output retained a private frame");
            Expect(nosub_camera_output_send(bgra.data(), int32_t(bgra.size())) < 0, "Disabled output accepted a frame");
        }
        nosub_camera_output_shutdown();
        Expect(Read(first, 16), "Quit did not black out cached reader");
        std::cout << "Five Enable/Disable cycles, unchanged cached readers, two consumers, stale input, cross-thread callers and quit passed (no device installed)\n";
        result = 0;
    } catch (const std::exception& error) { std::cerr << error.what() << "\n"; }
    nosub_camera_output_shutdown();
    if (mf) MFShutdown();
    if (com) CoUninitialize();
    return result;
}
