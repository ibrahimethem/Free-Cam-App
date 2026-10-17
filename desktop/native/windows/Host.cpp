#include "Common.h"
#include <mfvirtualcamera.h>
#include <wrl/client.h>
#include <sddl.h>
#include <bcrypt.h>
#include <shellapi.h>
#include <thread>
#include <mutex>
#include <atomic>
#include <memory>
#include <array>
#include <future>

using Microsoft::WRL::ComPtr;
using Callback = void(__cdecl*)(int32_t, const char*);
namespace {
HMODULE ThisModule() {
    HMODULE module = nullptr;
    GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                      reinterpret_cast<LPCWSTR>(&ThisModule), &module);
    return module;
}
std::wstring Directory() {
    wchar_t path[32768]{};
    if (!GetModuleFileNameW(ThisModule(), path, ARRAYSIZE(path))) return {};
    std::wstring value(path);
    return value.substr(0, value.find_last_of(L"\\/"));
}
std::wstring UserSid() {
    NoSub::Handle token;
    HANDLE raw = nullptr;
    if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &raw)) return {};
    token.reset(raw);
    DWORD length = 0;
    GetTokenInformation(token.get(), TokenUser, nullptr, 0, &length);
    std::vector<uint8_t> buffer(length);
    if (!GetTokenInformation(token.get(), TokenUser, buffer.data(), length, &length)) return {};
    LPWSTR sid = nullptr;
    if (!ConvertSidToStringSidW(reinterpret_cast<TOKEN_USER*>(buffer.data())->User.Sid, &sid)) return {};
    std::wstring result(sid); LocalFree(sid); return result;
}
struct Publisher {
    NoSub::Handle stop{CreateEventW(nullptr, TRUE, FALSE, nullptr)};
    std::mutex mutex;
    std::vector<uint8_t> latest = std::vector<uint8_t>(NoSub::FrameBytes);
    std::vector<uint8_t> scratch = std::vector<uint8_t>(NoSub::FrameBytes);
    ULONGLONG timestamp = 0;
    bool enabled = false;
    std::wstring pipeName;
    PSECURITY_DESCRIPTOR security = nullptr;
    std::array<std::thread, 4> servers;
    std::thread lifetime;
    ComPtr<IMFVirtualCamera> camera;
    bool com = false, mf = false;

    ~Publisher() {
        if (stop) SetEvent(stop.get());
        if (lifetime.joinable()) lifetime.join();
    }

    // Only the lifetime thread owns/releases COM/MF objects. Python frame
    // workers are short-lived and change on each Enable/Disable cycle.
    void Cleanup() {
        if (stop) SetEvent(stop.get());
        for (auto& thread : servers) if (thread.joinable()) thread.join();
        if (camera) { camera->Stop(); camera->Shutdown(); camera.Reset(); }
        if (security) LocalFree(security);
        if (mf) MFShutdown();
        if (com) CoUninitialize();
    }

    HRESULT Launch() {
        auto started = std::make_shared<std::promise<HRESULT>>();
        auto ready = started->get_future();
        lifetime = std::thread([this, started] {
            HRESULT result = E_FAIL;
            try { result = Start(); } catch (...) { result = E_OUTOFMEMORY; }
            started->set_value(result);
            if (SUCCEEDED(result)) WaitForSingleObject(stop.get(), INFINITE);
            Cleanup();
        });
        return ready.get();
    }

    void Enable(bool value) {
        std::lock_guard lock(mutex);
        enabled = value;
        timestamp = 0;
        NoSub::Black(latest.data());
        NoSub::Black(scratch.data());
    }

    void Serve() {
        SECURITY_ATTRIBUTES sa{sizeof(sa), security, FALSE};
        while (WaitForSingleObject(stop.get(), 0) != WAIT_OBJECT_0) {
            NoSub::Handle pipe(CreateNamedPipeW(pipeName.c_str(), PIPE_ACCESS_DUPLEX | FILE_FLAG_OVERLAPPED,
                PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT | PIPE_REJECT_REMOTE_CLIENTS,
                4, DWORD(NoSub::FrameBytes + sizeof(NoSub::Header)), 16, 100, &sa));
            if (!pipe) {
                // Disconnected clients may briefly retain handles to old pipe
                // instances. Do not permanently lose a server slot during retry.
                if (WaitForSingleObject(stop.get(), 20) == WAIT_OBJECT_0) return;
                continue;
            }
            NoSub::Handle event(CreateEventW(nullptr, TRUE, FALSE, nullptr));
            if (!event) return;
            OVERLAPPED ov{}; ov.hEvent = event.get();
            BOOL connected = ConnectNamedPipe(pipe.get(), &ov);
            if (!connected) {
                const DWORD error = GetLastError();
                if (error == ERROR_IO_PENDING) {
                    HANDLE events[]{event.get(), stop.get()};
                    if (WaitForMultipleObjects(2, events, FALSE, INFINITE) != WAIT_OBJECT_0) {
                        CancelIoEx(pipe.get(), &ov);
                        DWORD ignored = 0; GetOverlappedResult(pipe.get(), &ov, &ignored, TRUE);
                        break;
                    }
                    DWORD ignored = 0;
                    connected = GetOverlappedResult(pipe.get(), &ov, &ignored, FALSE);
                } else connected = error == ERROR_PIPE_CONNECTED;
            }
            if (!connected) continue;
            std::vector<uint8_t> frame(NoSub::FrameBytes);
            while (WaitForSingleObject(stop.get(), 0) != WAIT_OBJECT_0) {
                uint8_t request = 0;
                // A paused consumer is not a broken connection. This read can
                // wait idle, but the stop event cancels it immediately on quit.
                if (!NoSub::Transfer(pipe.get(), &request, 1, false, stop.get(), INFINITE) || request != 1) break;
                {
                    std::lock_guard lock(mutex);
                    if (enabled && timestamp && GetTickCount64() - timestamp < 1000) frame = latest;
                    else NoSub::Black(frame.data());
                }
                NoSub::Header header{NoSub::Magic, 1, NoSub::Width, NoSub::Height, DWORD(NoSub::FrameBytes), {}};
                if (!NoSub::Transfer(pipe.get(), &header, sizeof(header), true, stop.get()) ||
                    !NoSub::Transfer(pipe.get(), frame.data(), DWORD(frame.size()), true, stop.get())) break;
            }
            DisconnectNamedPipe(pipe.get());
        }
    }

    HRESULT Start() {
        if (!stop) return HRESULT_FROM_WIN32(GetLastError());
        HRESULT hr = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
        if (FAILED(hr)) return hr;
        com = true;
        hr = MFStartup(MF_VERSION); if (FAILED(hr)) return hr;
        mf = true;
        const auto sid = UserSid();
        if (sid.empty()) return E_ACCESSDENIED;
        // Only this Windows user, SYSTEM and Local Service (Frame Server).
        const auto sddl = L"D:P(A;;GA;;;" + sid + L")(A;;GRGW;;;SY)(A;;GRGW;;;LS)";
        if (!ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl.c_str(), SDDL_REVISION_1, &security, nullptr))
            return HRESULT_FROM_WIN32(GetLastError());
        uint8_t random[16]{};
        if (BCryptGenRandom(nullptr, random, sizeof(random), BCRYPT_USE_SYSTEM_PREFERRED_RNG) < 0) return E_FAIL;
        pipeName = NoSub::PipePrefix;
        for (auto byte : random) { pipeName += L"0123456789abcdef"[byte >> 4]; pipeName += L"0123456789abcdef"[byte & 15]; }
        NoSub::Black(latest.data());
#ifndef NOSUB_TRANSPORT_TEST
        hr = MFCreateVirtualCamera(MFVirtualCameraType_SoftwareCameraSource, MFVirtualCameraLifetime_Session,
            MFVirtualCameraAccess_CurrentUser, L"NoSub Camera", NoSub::SourceId, nullptr, 0, &camera);
        if (FAILED(hr)) return hr;
        hr = camera->SetString(NoSub::PipeAttribute, pipeName.c_str());
        if (FAILED(hr)) return hr;
#endif
        for (auto& thread : servers) thread = std::thread([this] { Serve(); });
#ifdef NOSUB_TRANSPORT_TEST
        return S_OK; // Same real pipe/lifecycle, but never register a test device.
#else
        return camera->Start(nullptr);
#endif
    }
};
std::unique_ptr<Publisher> publisher;
std::mutex publisherMutex;
std::atomic<bool> installing{false};
}

extern "C" int32_t __cdecl nosub_camera_available() {
    wchar_t path[32768]{}; DWORD bytes = sizeof(path);
    const auto status = RegGetValueW(HKEY_LOCAL_MACHINE, NoSub::RegistryKey, nullptr,
        RRF_RT_REG_SZ | RRF_SUBKEY_WOW6464KEY, nullptr, path, &bytes);
    return status == ERROR_SUCCESS && GetFileAttributesW(path) != INVALID_FILE_ATTRIBUTES ? 1 : 0;
}

extern "C" void __cdecl nosub_camera_request(int32_t install, Callback callback) {
    if (installing.exchange(true)) { callback(2, "Another camera setup is already running."); return; }
    std::thread([install, callback] {
        const auto exe = Directory() + L"\\NoSubCameraSetup.exe";
        SHELLEXECUTEINFOW request{sizeof(request)};
        request.fMask = SEE_MASK_NOCLOSEPROCESS | SEE_MASK_FLAG_NO_UI;
        request.lpVerb = L"runas"; request.lpFile = exe.c_str();
        request.lpParameters = install ? L"--install" : L"--uninstall";
        request.nShow = SW_SHOWNORMAL;
        if (!ShellExecuteExW(&request)) {
            callback(2, GetLastError() == ERROR_CANCELLED ? "Camera setup was cancelled. Nothing was changed."
                                                        : "Camera setup could not start.");
        } else {
            NoSub::Handle process(request.hProcess);
            WaitForSingleObject(process.get(), INFINITE);
            DWORD code = 1; GetExitCodeProcess(process.get(), &code);
            callback(code == 0 ? 1 : 2, code == 0
                ? (install ? "NoSub Camera installed. Enable camera output to use it." : "NoSub Camera removed.")
                : "Camera setup failed. Close video apps and try again; see the setup error dialog.");
        }
        installing = false;
    }).detach();
}

extern "C" int32_t __cdecl nosub_camera_output_start() {
    std::lock_guard lock(publisherMutex);
    if (publisher) { publisher->Enable(true); return 1; }
    try {
        auto candidate = std::make_unique<Publisher>();
        const HRESULT hr = candidate->Launch();
        if (FAILED(hr)) return int32_t(hr);
        candidate->Enable(true);
        publisher = std::move(candidate);
        return 1;
    } catch (...) { return int32_t(E_OUTOFMEMORY); }
}
extern "C" int32_t __cdecl nosub_camera_output_send(const void* data, int32_t length) {
    std::lock_guard lock(publisherMutex);
    if (!publisher || !publisher->enabled) return -1;
    if (!data && !length) {
        std::lock_guard frameLock(publisher->mutex);
        publisher->timestamp = 0;
        NoSub::Black(publisher->latest.data());
        return 1;
    }
    if (!data || length != NoSub::BgraBytes) return -1;
    NoSub::BgraToNv12(static_cast<const uint8_t*>(data), publisher->scratch.data());
    std::lock_guard frameLock(publisher->mutex);
    publisher->latest.swap(publisher->scratch);
    publisher->timestamp = GetTickCount64();
    return 1;
}
extern "C" void __cdecl nosub_camera_output_stop() {
    std::lock_guard lock(publisherMutex);
    // Keep the same virtual device, activation attributes and pipe alive. Video
    // apps may keep their media source cached while output is disabled. Replacing
    // its random pipe on every toggle strands that source on a dead endpoint.
    if (publisher) publisher->Enable(false);
}
extern "C" void __cdecl nosub_camera_output_shutdown() {
    std::lock_guard lock(publisherMutex);
    publisher.reset();
}
#ifdef NOSUB_TRANSPORT_TEST
extern "C" const wchar_t* nosub_camera_test_pipe() {
    return publisher ? publisher->pipeName.c_str() : L"";
}
#endif
extern "C" void __cdecl nosub_camera_activity(int32_t) {
    // Windows tray operation does not use App Nap. Do not alter power settings.
}
