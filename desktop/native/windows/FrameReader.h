#pragma once
#include "Common.h"
#include <chrono>

// Adapter name matches Microsoft's lifecycle sample, but no synthetic imagery
// or physical camera access remains in this generator.
class SimpleFrameGenerator {
    NoSub::Handle pipe_;
    std::wstring name_;
    std::vector<uint8_t> pixels_ = std::vector<uint8_t>(NoSub::FrameBytes);
    std::chrono::steady_clock::time_point next_{};
public:
    HRESULT Initialize(IMFMediaType* type);
    void SetPipeName(const std::wstring& name) { pipe_.reset(); name_ = name; next_ = {}; }
    HRESULT CreateFrame(BYTE* buffer, DWORD length, LONG pitch, ULONG unused);
};
