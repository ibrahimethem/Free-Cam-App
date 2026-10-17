#pragma once
#include <algorithm>
#include <cstdint>
#include <cstddef>

namespace NoSub {
inline constexpr int Width = 1920, Height = 1080;
inline constexpr size_t BgraBytes = size_t(Width) * Height * 4;
inline constexpr size_t FrameBytes = size_t(Width) * Height * 3 / 2;
inline uint8_t Clip(int value) { return uint8_t(std::clamp(value, 0, 255)); }
inline void Black(uint8_t* frame) {
    std::fill_n(frame, size_t(Width) * Height, uint8_t(16));
    std::fill_n(frame + size_t(Width) * Height, size_t(Width) * Height / 2, uint8_t(128));
}
// BT.601 studio-range NV12, matching the media type advertised to Frame Server.
inline void BgraToNv12(const uint8_t* bgra, uint8_t* out) {
    for (int y = 0; y < Height; y += 2) {
        for (int x = 0; x < Width; x += 2) {
            int sumR = 0, sumG = 0, sumB = 0;
            for (int dy = 0; dy < 2; ++dy) for (int dx = 0; dx < 2; ++dx) {
                const auto index = size_t(y + dy) * Width + x + dx;
                const auto* p = bgra + index * 4;
                const int b = p[0], g = p[1], r = p[2];
                out[index] = Clip(((66 * r + 129 * g + 25 * b + 128) >> 8) + 16);
                sumR += r; sumG += g; sumB += b;
            }
            const int r = (sumR + 2) / 4, g = (sumG + 2) / 4, b = (sumB + 2) / 4;
            const auto uv = size_t(Width) * Height + size_t(y / 2) * Width + x;
            out[uv] = Clip(((-38 * r - 74 * g + 112 * b + 128) >> 8) + 128);
            out[uv + 1] = Clip(((112 * r - 94 * g - 18 * b + 128) >> 8) + 128);
        }
    }
}
}
