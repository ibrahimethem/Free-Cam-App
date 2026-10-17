#pragma once
#include <windows.h>
#include <mfapi.h>
#include <string>
#include <vector>
#include <cstdint>
#include "FramePixels.h"

namespace NoSub {
inline const GUID SourceClsid = {0xa9179078, 0x9633, 0x49c0, {0xa3, 0x6e, 0x31, 0x2b, 0x7e, 0x86, 0x1a, 0x70}};
inline constexpr wchar_t SourceId[] = L"{A9179078-9633-49C0-A36E-312B7E861A70}";
inline const GUID PipeAttribute = {0x266d0d98, 0xe902, 0x4aef, {0x8d, 0xf1, 0x76, 0x7f, 0xd8, 0xc0, 0x71, 0x12}};
inline constexpr wchar_t PipePrefix[] = L"\\\\.\\pipe\\NoSubCam.Frame.";
inline constexpr uint32_t Magic = 0x3143534e; // NSC1
inline constexpr wchar_t RegistryKey[] = L"SOFTWARE\\Classes\\CLSID\\{A9179078-9633-49C0-A36E-312B7E861A70}\\InprocServer32";
struct Header { uint32_t magic, version, width, height, bytes, reserved[3]; };
static_assert(sizeof(Header) == 32);

inline bool ValidPipeName(const std::wstring& name) {
    const std::wstring prefix = PipePrefix;
    if (name.size() != prefix.size() + 32 || name.compare(0, prefix.size(), prefix)) return false;
    for (auto c : name.substr(prefix.size())) if (!((c >= L'0' && c <= L'9') || (c >= L'a' && c <= L'f'))) return false;
    return true;
}

class Handle {
    HANDLE value_ = INVALID_HANDLE_VALUE;
public:
    explicit Handle(HANDLE value = INVALID_HANDLE_VALUE) : value_(value) {}
    ~Handle() { reset(); }
    Handle(const Handle&) = delete;
    Handle& operator=(const Handle&) = delete;
    HANDLE get() const { return value_; }
    explicit operator bool() const { return value_ && value_ != INVALID_HANDLE_VALUE; }
    void reset(HANDLE value = INVALID_HANDLE_VALUE) {
        if (*this) CloseHandle(value_);
        value_ = value;
    }
};

// Bounded overlapped I/O. Cancellation is drained before OVERLAPPED/event storage
// is destroyed; neither a stopped host nor a malicious peer can hang shutdown.
inline bool Transfer(HANDLE pipe, void* data, DWORD length, bool writing, HANDLE stop = nullptr) {
    const ULONGLONG deadline = GetTickCount64() + 100;
    auto* cursor = static_cast<uint8_t*>(data);
    while (length) {
        Handle event(CreateEventW(nullptr, TRUE, FALSE, nullptr));
        if (!event) return false;
        OVERLAPPED ov{}; ov.hEvent = event.get();
        DWORD count = 0;
        const BOOL ready = writing ? WriteFile(pipe, cursor, length, &count, &ov)
                                   : ReadFile(pipe, cursor, length, &count, &ov);
        if (!ready) {
            if (GetLastError() != ERROR_IO_PENDING) return false;
            const ULONGLONG now = GetTickCount64();
            const DWORD timeout = now >= deadline ? 0 : DWORD(deadline - now);
            HANDLE events[] = {event.get(), stop};
            const DWORD wait = WaitForMultipleObjects(stop ? 2 : 1, events, FALSE, timeout);
            if (wait != WAIT_OBJECT_0) {
                CancelIoEx(pipe, &ov);
                GetOverlappedResult(pipe, &ov, &count, TRUE);
                return false;
            }
            if (!GetOverlappedResult(pipe, &ov, &count, FALSE)) return false;
        }
        if (!count) return false;
        cursor += count; length -= count;
    }
    return true;
}
}
