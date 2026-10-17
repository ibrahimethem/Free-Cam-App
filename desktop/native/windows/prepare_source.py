"""Stage a pinned Microsoft sample in ignored build output; never edit upstream.

Keep its IMFMediaSourceEx/event/allocator lifecycle, remove hardware-camera
wrapping and synthetic images, and feed our bounded local frame pipe instead.
Every structural replacement fails closed if upstream is unexpectedly different.
"""
import argparse
from pathlib import Path

CLSID = "A9179078-9633-49C0-A36E-312B7E861A70"


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Unexpected pinned sample structure: {old[:70]!r}")
    return text.replace(old, new, 1)


def transform(name, text):
    text = text.replace("7B89B92E-FE71-42D0-8A41-E137D06EA184", CLSID)
    if name == "VirtualCameraMediaSource.h":
        text = replace_once(text,
            "0x7b89b92e, 0xfe71, 0x42d0, 0x8a, 0x41, 0xe1, 0x37, 0xd0, 0x6e, 0xa1, 0x84",
            "0xa9179078, 0x9633, 0x49c0, 0xa3, 0x6e, 0x31, 0x2b, 0x7e, 0x86, 0x1a, 0x70")
    if name == "pch.h":
        for header in ("EventHandler.h", "HWMediaSource.h", "HWMediaStream.h", "AugmentedMediaSource.h", "AugmentedMediaStream.h"):
            text = replace_once(text, f'#include "{header}"', "")
        text = '#include "Common.h"\n#include <strsafe.h>\n' + text
    if name == "VirtualCameraMediaSourceActivate.h":
        text = "\n".join(line for line in text.splitlines()
                         if "m_spHWMediaSrc;" not in line and "m_spAugmentedMediaSrc;" not in line)
    if name == "VirtualCameraMediaSourceActivate.cpp":
        start = text.index("        bool bIsWrappingCamera = false;")
        end = text.index("    // IMFAttributes (inherits by IMFActivate)")
        text = text[:start] + '''        if (!m_spSimpleMediaSrc) {
            m_spSimpleMediaSrc = winrt::make_self<SimpleMediaSource>();
            HRESULT hr = m_spSimpleMediaSrc->Initialize(this);
            if (FAILED(hr)) {
                m_spSimpleMediaSrc->Shutdown();
                m_spSimpleMediaSrc = nullptr;
                return hr;
            }
        }
        return m_spSimpleMediaSrc->QueryInterface(riid, ppv);
    }

    IFACEMETHODIMP VirtualCameraMediaSourceActivate::ShutdownObject() {
        if (m_spSimpleMediaSrc) m_spSimpleMediaSrc->Shutdown();
        m_spSimpleMediaSrc = nullptr;
        return S_OK;
    }
    IFACEMETHODIMP VirtualCameraMediaSourceActivate::DetachObject() {
        m_spSimpleMediaSrc = nullptr;
        return S_OK;
    }

''' + text[end:]
    if name == "SimpleMediaSource.cpp":
        text = replace_once(text,
            "RETURN_IF_FAILED(m_streamList[i]->Initialize(this, i, MFSampleAllocatorUsage_UsesProvidedAllocator));",
            '''RETURN_IF_FAILED(m_streamList[i]->Initialize(this, i, MFSampleAllocatorUsage_UsesProvidedAllocator));
            WCHAR pipe[256] = {};
            RETURN_IF_FAILED(pAttributes->GetString(NoSub::PipeAttribute, pipe, ARRAYSIZE(pipe), nullptr));
            RETURN_HR_IF(E_INVALIDARG, !NoSub::ValidPipeName(pipe));
            m_streamList[i]->SetFramePipeName(pipe);''')
    if name == "SimpleMediaStream.h":
        text = replace_once(text, "        DWORD Id() const", """        void SetFramePipeName(const wchar_t* name) { m_framePipe = name; }
        std::wstring m_framePipe;
        DWORD Id() const""")
    if name == "SimpleMediaStream.cpp":
        text = replace_once(text, "#define NUM_IMAGE_ROWS 480", "#define NUM_IMAGE_ROWS 1080")
        text = replace_once(text, "#define NUM_IMAGE_COLS 640", "#define NUM_IMAGE_COLS 1920")
        text = replace_once(text, "const uint32_t NUM_MEDIATYPES = 2;", "const uint32_t NUM_MEDIATYPES = 1;")
        text = replace_once(text, "spMediaType->SetGUID(MF_MT_SUBTYPE, MFVideoFormat_NV12);",
                            "spMediaType->SetGUID(MF_MT_SUBTYPE, MFVideoFormat_NV12);\n        spMediaType->SetUINT32(MF_MT_YUV_MATRIX, MFVideoTransferMatrix_BT601);\n        spMediaType->SetUINT32(MF_MT_VIDEO_NOMINAL_RANGE, MFNominalRange_16_235);")
        start = text.index("        RETURN_IF_FAILED(MFCreateMediaType(&spMediaType));", text.index("mediaTypeList[0] ="))
        end = text.index("        RETURN_IF_FAILED(MFCreateAttributes(&m_spAttributes", start)
        text = text[:start] + text[end:]
        text = replace_once(text, "RETURN_IF_FAILED(m_spFrameGenerator->Initialize(m_spMediaType.get()));",
                            "RETURN_IF_FAILED(m_spFrameGenerator->Initialize(m_spMediaType.get()));\n            m_spFrameGenerator->SetPipeName(m_framePipe);")
        # Always unlock an allocator buffer, including when frame generation fails.
        text = replace_once(text,
            "RETURN_IF_FAILED(m_spFrameGenerator->CreateFrame(pbuf, bufferLength, pitch, m_rgbMask));",
            "HRESULT frameResult = m_spFrameGenerator->CreateFrame(pbuf, bufferLength, pitch, m_rgbMask);")
        text = replace_once(text, "RETURN_IF_FAILED(buffer2D->Unlock2D());",
                            "RETURN_IF_FAILED(buffer2D->Unlock2D());\n        RETURN_IF_FAILED(frameResult);")
    return text


def prepare(reference, destination):
    source = reference / "Samples/VirtualCamera/VirtualCameraMediaSource"
    destination.mkdir(parents=True, exist_ok=True)
    names = ("pch.h", "SimpleMediaSource.cpp", "SimpleMediaSource.h", "SimpleMediaStream.cpp",
             "SimpleMediaStream.h", "VirtualCameraMediaSource.h", "VirtualCameraMediaSourceActivate.cpp",
             "VirtualCameraMediaSourceActivate.h", "winrtCommon.cpp", "dllmain.cpp")
    for name in names:
        (destination / name).write_text(transform(name, (source / name).read_text(encoding="utf-8-sig")), encoding="utf-8")
    # Header name retained so the official sample's lifecycle code stays unchanged.
    (destination / "SimpleFrameGenerator.h").write_text('#include "FrameReader.h"\n', encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    prepare(args.reference, args.destination)
