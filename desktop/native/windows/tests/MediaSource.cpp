// Instantiate the DLL directly, without registering/installing a device.
#include "Common.h"
#include <mfidl.h>
#include <mferror.h>
#include <wrl/client.h>
#include <iostream>
#include <stdexcept>

using Microsoft::WRL::ComPtr;
static void Check(HRESULT hr) {
    if (FAILED(hr)) {
        std::cerr << "Media source check failed: 0x" << std::hex << uint32_t(hr) << "\n";
        throw std::runtime_error("HRESULT failure");
    }
}
static ComPtr<IMFMediaEvent> Event(IMFMediaEventGenerator* source, MediaEventType wanted) {
    for (int i = 0; i < 8; ++i) {
        ComPtr<IMFMediaEvent> event;
        Check(source->GetEvent(MF_EVENT_FLAG_NO_WAIT, &event));
        MediaEventType type; Check(event->GetType(&type));
        HRESULT status = E_FAIL; Check(event->GetStatus(&status)); Check(status);
        if (type == wanted) return event;
    }
    throw std::runtime_error("Expected event missing");
}
int wmain(int argc, wchar_t** argv) {
    if (argc != 2) return 2;
    ComPtr<IMFMediaSourceEx> source;
    ComPtr<IMFActivate> activation;
    bool com = false, mf = false;
    HMODULE library = nullptr;
    int result = 1;
    try {
        Check(CoInitializeEx(nullptr, COINIT_MULTITHREADED)); com = true;
        Check(MFStartup(MF_VERSION)); mf = true;
        library = LoadLibraryExW(argv[1], nullptr, LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32);
        if (!library) Check(HRESULT_FROM_WIN32(GetLastError()));
        using Factory = HRESULT(__stdcall*)(REFCLSID, REFIID, void**);
        const auto factoryFunction = reinterpret_cast<Factory>(GetProcAddress(library, "DllGetClassObject"));
        if (!factoryFunction) throw std::runtime_error("COM export missing");
        ComPtr<IClassFactory> factory;
        Check(factoryFunction(NoSub::SourceClsid, IID_PPV_ARGS(&factory)));
        Check(factory->CreateInstance(nullptr, IID_PPV_ARGS(&activation)));
        // A deliberately nonexistent, well-formed pipe: no producer means black.
        const auto name = std::wstring(NoSub::PipePrefix) + std::wstring(32, L'0');
        Check(activation->SetString(NoSub::PipeAttribute, name.c_str()));
        Check(activation->ActivateObject(IID_PPV_ARGS(&source)));
        ComPtr<IMFPresentationDescriptor> pd;
        Check(source->CreatePresentationDescriptor(&pd));
        DWORD count = 0; Check(pd->GetStreamDescriptorCount(&count));
        if (count != 1) throw std::runtime_error("Wrong stream count");
        Check(pd->SelectStream(0));
        ComPtr<IMFStreamDescriptor> descriptor; BOOL selected = FALSE;
        Check(pd->GetStreamDescriptorByIndex(0, &selected, &descriptor));
        ComPtr<IMFMediaTypeHandler> handler; Check(descriptor->GetMediaTypeHandler(&handler));
        ComPtr<IMFMediaType> type; Check(handler->GetCurrentMediaType(&type));
        GUID subtype{}; UINT32 width = 0, height = 0;
        Check(type->GetGUID(MF_MT_SUBTYPE, &subtype));
        Check(MFGetAttributeSize(type.Get(), MF_MT_FRAME_SIZE, &width, &height));
        if (subtype != MFVideoFormat_NV12 || width != 1920 || height != 1080)
            throw std::runtime_error("Wrong media format");
        ComPtr<IMFSampleAllocatorControl> allocatorControl; Check(source.As(&allocatorControl));
        ComPtr<IMFVideoSampleAllocator> allocator;
        Check(MFCreateVideoSampleAllocatorEx(IID_PPV_ARGS(&allocator)));
        Check(allocatorControl->SetDefaultAllocator(0, allocator.Get()));
        PROPVARIANT position{};
        Check(source->Start(pd.Get(), nullptr, &position));
        auto newStream = Event(source.Get(), MENewStream);
        PROPVARIANT value{}; Check(newStream->GetValue(&value));
        ComPtr<IMFMediaStream> stream;
        HRESULT streamResult = value.vt == VT_UNKNOWN ? value.punkVal->QueryInterface(IID_PPV_ARGS(&stream)) : E_FAIL;
        PropVariantClear(&value); Check(streamResult);
        Check(stream->RequestSample(nullptr));
        auto sampleEvent = Event(stream.Get(), MEMediaSample);
        Check(sampleEvent->GetValue(&value));
        ComPtr<IMFSample> sample;
        HRESULT sampleResult = value.vt == VT_UNKNOWN ? value.punkVal->QueryInterface(IID_PPV_ARGS(&sample)) : E_FAIL;
        PropVariantClear(&value); Check(sampleResult);
        LONGLONG duration = 0; Check(sample->GetSampleDuration(&duration));
        if (duration != 333333) throw std::runtime_error("Wrong sample timing");
        ComPtr<IMFMediaBuffer> buffer; Check(sample->GetBufferByIndex(0, &buffer));
        ComPtr<IMF2DBuffer2> twoD; Check(buffer.As(&twoD));
        BYTE* pixels = nullptr; BYTE* start = nullptr; DWORD length = 0; LONG pitch = 0;
        Check(twoD->Lock2DSize(MF2DBuffer_LockFlags_Read, &pixels, &pitch, &start, &length));
        const bool black = pixels && pitch >= 1920 && pixels[0] == 16 && pixels[size_t(pitch) * 1080] == 128;
        Check(twoD->Unlock2D());
        if (!black) throw std::runtime_error("Disconnected source is not black");
        Check(source->Stop());
        result = 0;
        std::cout << "COM activation, 1080p NV12 sample allocation, events, timing and black fallback passed (no device installed)\n";
    } catch (const std::exception& error) { std::cerr << error.what() << "\n"; }
    if (source) source->Shutdown();
    source.Reset();
    if (activation) activation->ShutdownObject();
    activation.Reset();
    if (library) FreeLibrary(library);
    if (mf) MFShutdown();
    if (com) CoUninitialize();
    return result;
}
