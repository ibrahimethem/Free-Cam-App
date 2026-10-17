#include "FrameReader.h"
#include <mferror.h>
#include <thread>
#include <cstring>

HRESULT SimpleFrameGenerator::Initialize(IMFMediaType* type) {
    if (!type) return E_POINTER;
    GUID format{}; UINT32 width = 0, height = 0;
    if (FAILED(type->GetGUID(MF_MT_SUBTYPE, &format)) || format != MFVideoFormat_NV12 ||
        FAILED(MFGetAttributeSize(type, MF_MT_FRAME_SIZE, &width, &height)) ||
        width != NoSub::Width || height != NoSub::Height) return MF_E_INVALIDMEDIATYPE;
    return S_OK;
}

HRESULT SimpleFrameGenerator::CreateFrame(BYTE* buffer, DWORD length, LONG pitch, ULONG) {
    if (!buffer || pitch < NoSub::Width || size_t(length) < size_t(pitch) * NoSub::Height * 3 / 2)
        return E_INVALIDARG;
    const auto now = std::chrono::steady_clock::now();
    if (next_ > now) std::this_thread::sleep_until(next_);
    next_ = std::max(next_ + std::chrono::nanoseconds(33333333), std::chrono::steady_clock::now());
    NoSub::Black(pixels_.data());
    if (!pipe_ && NoSub::ValidPipeName(name_)) {
        // A low-privilege app hosting a pipe must never impersonate Frame Server.
        pipe_.reset(CreateFileW(name_.c_str(), GENERIC_READ | GENERIC_WRITE, 0, nullptr,
            OPEN_EXISTING, FILE_FLAG_OVERLAPPED | SECURITY_SQOS_PRESENT | SECURITY_IDENTIFICATION, nullptr));
    }
    if (pipe_) {
        uint8_t request = 1;
        NoSub::Header header{};
        if (!NoSub::Transfer(pipe_.get(), &request, 1, true) ||
            !NoSub::Transfer(pipe_.get(), &header, sizeof(header), false) ||
            header.magic != NoSub::Magic || header.version != 1 || header.width != NoSub::Width ||
            header.height != NoSub::Height || header.bytes != NoSub::FrameBytes ||
            !NoSub::Transfer(pipe_.get(), pixels_.data(), DWORD(pixels_.size()), false)) {
            pipe_.reset();
            NoSub::Black(pixels_.data());
        }
    }
    for (int y = 0; y < NoSub::Height * 3 / 2; ++y)
        std::memcpy(buffer + size_t(y) * pitch, pixels_.data() + size_t(y) * NoSub::Width, NoSub::Width);
    return S_OK;
}
