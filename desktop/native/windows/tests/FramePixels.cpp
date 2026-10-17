#include "FramePixels.h"
#include <vector>
#include <iostream>

int main() {
    std::vector<uint8_t> bgra(NoSub::BgraBytes), nv12(NoSub::FrameBytes);
    NoSub::BgraToNv12(bgra.data(), nv12.data());
    if (nv12[0] != 16 || nv12[NoSub::Width * NoSub::Height] != 128) return 1;
    std::fill(bgra.begin(), bgra.end(), 255);
    NoSub::BgraToNv12(bgra.data(), nv12.data());
    if (nv12[0] != 235 || nv12.back() != 128) return 2;
    for (size_t i = 0; i < bgra.size(); i += 4) {
        bgra[i] = 0; bgra[i + 1] = 0; bgra[i + 2] = 255; bgra[i + 3] = 255;
    }
    NoSub::BgraToNv12(bgra.data(), nv12.data());
    if (nv12[0] != 82 || nv12[NoSub::Width * NoSub::Height] != 90 || nv12.back() != 240) return 3;
    NoSub::Black(nv12.data());
    for (size_t i = 0; i < nv12.size(); ++i)
        if (nv12[i] != (i < NoSub::Width * NoSub::Height ? 16 : 128)) return 4;
    std::cout << "NV12 black/white/red conversion and full-frame clear passed\n";
    return 0;
}
