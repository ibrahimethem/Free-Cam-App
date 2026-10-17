// This is the only elevated process. The desktop host stays non-administrative.
// Install into Program Files so Frame Server never loads a user-writable DLL.
#include "Common.h"
#include <shlobj.h>
#include <filesystem>
#include <stdexcept>

namespace fs = std::filesystem;
namespace {
constexpr const wchar_t* Notices[] = {L"Microsoft-Windows-Camera.txt", L"Microsoft-WIL.txt"};
void Check(LSTATUS status) { if (status != ERROR_SUCCESS) throw std::runtime_error("Registry operation failed"); }
fs::path Destination() {
    PWSTR folder = nullptr;
    if (FAILED(SHGetKnownFolderPath(FOLDERID_ProgramFiles, 0, nullptr, &folder)))
        throw std::runtime_error("Program Files unavailable");
    fs::path result(folder); CoTaskMemFree(folder);
    return result / L"NoSub Studio Camera" / L"NoSubCamera.dll";
}
std::wstring RegisteredPath() {
    wchar_t path[32768]{}; DWORD size = sizeof(path);
    const auto status = RegGetValueW(HKEY_LOCAL_MACHINE, NoSub::RegistryKey, nullptr,
        RRF_RT_REG_SZ | RRF_SUBKEY_WOW6464KEY, nullptr, path, &size);
    if (status == ERROR_FILE_NOT_FOUND || status == ERROR_PATH_NOT_FOUND) return {};
    Check(status); return path;
}
void Install() {
    wchar_t path[32768]{};
    if (!GetModuleFileNameW(nullptr, path, ARRAYSIZE(path))) throw std::runtime_error("Setup path unavailable");
    const auto source = fs::path(path).parent_path() / L"NoSubCamera.dll";
    const auto destination = Destination();
    const auto previous = RegisteredPath();
    if (!previous.empty() && _wcsicmp(previous.c_str(), destination.c_str()))
        throw std::runtime_error("Unexpected COM registration: refusing to overwrite another path");
    // Do not follow a pre-existing junction/reparse point into another directory.
    const auto directory = destination.parent_path();
    if (!fs::exists(directory)) fs::create_directory(directory);
    const auto attributes = GetFileAttributesW(directory.c_str());
    if (attributes == INVALID_FILE_ATTRIBUTES || (attributes & FILE_ATTRIBUTE_REPARSE_POINT))
        throw std::runtime_error("Unsafe installation directory");
    if (fs::exists(destination) && (GetFileAttributesW(destination.c_str()) & FILE_ATTRIBUTE_REPARSE_POINT))
        throw std::runtime_error("Unsafe installation file");
    const auto notices = directory / L"licenses";
    if (!fs::exists(notices)) fs::create_directory(notices);
    if (GetFileAttributesW(notices.c_str()) & FILE_ATTRIBUTE_REPARSE_POINT)
        throw std::runtime_error("Unsafe license directory");
    for (const auto* name : Notices) {
        const auto target = notices / name;
        if (fs::exists(target) && (GetFileAttributesW(target.c_str()) & FILE_ATTRIBUTE_REPARSE_POINT))
            throw std::runtime_error("Unsafe license file");
        if (!CopyFileW((source.parent_path() / L"licenses" / name).c_str(), target.c_str(), FALSE))
            throw std::runtime_error("Required third-party license notice missing");
    }
    if (!CopyFileW(source.c_str(), destination.c_str(), FALSE))
        throw std::runtime_error("Cannot replace camera DLL: close camera/video apps and retry");
    HKEY key = nullptr;
    Check(RegCreateKeyExW(HKEY_LOCAL_MACHINE, NoSub::RegistryKey, 0, nullptr, 0,
                         KEY_SET_VALUE | KEY_WOW64_64KEY, nullptr, &key, nullptr));
    const auto value = destination.wstring();
    const auto first = RegSetValueExW(key, nullptr, 0, REG_SZ,
        reinterpret_cast<const BYTE*>(value.c_str()), DWORD((value.size() + 1) * sizeof(wchar_t)));
    constexpr wchar_t model[] = L"Both";
    const auto second = RegSetValueExW(key, L"ThreadingModel", 0, REG_SZ,
        reinterpret_cast<const BYTE*>(model), sizeof(model));
    RegCloseKey(key); Check(first); Check(second);
}
void Uninstall() {
    const auto destination = Destination();
    const auto registered = RegisteredPath();
    if (!registered.empty() && _wcsicmp(registered.c_str(), destination.c_str()))
        throw std::runtime_error("Unexpected COM registration: refusing removal");
    if (fs::exists(destination)) {
        if (GetFileAttributesW(destination.c_str()) & FILE_ATTRIBUTE_REPARSE_POINT)
            throw std::runtime_error("Unsafe installation file");
        // Delete only our one known DLL; never recursively remove a directory.
        if (!DeleteFileW(destination.c_str())) throw std::runtime_error("Camera DLL is in use: close video apps first");
    }
    HKEY classes = nullptr;
    Check(RegOpenKeyExW(HKEY_LOCAL_MACHINE, L"SOFTWARE\\Classes\\CLSID", 0,
                       DELETE | KEY_ENUMERATE_SUB_KEYS | KEY_QUERY_VALUE | KEY_SET_VALUE | KEY_WOW64_64KEY, &classes));
    const auto result = RegDeleteTreeW(classes, NoSub::SourceId);
    RegCloseKey(classes);
    if (result != ERROR_FILE_NOT_FOUND) Check(result);
    for (const auto* name : Notices) DeleteFileW((destination.parent_path() / L"licenses" / name).c_str());
    RemoveDirectoryW((destination.parent_path() / L"licenses").c_str());
    RemoveDirectoryW(destination.parent_path().c_str()); // succeeds only when empty
}
}
int wmain(int argc, wchar_t** argv) {
    try {
        if (argc != 2) return 2;
        if (std::wstring(argv[1]) == L"--install") Install();
        else if (std::wstring(argv[1]) == L"--uninstall") Uninstall();
        else return 2;
        return 0;
    } catch (...) {
        MessageBoxW(nullptr,
            L"NoSub Camera setup could not finish. Close all video apps and disable camera output, then retry. "
            L"Administrator approval is required. No system security settings need to be disabled.",
            L"NoSub Camera setup", MB_OK | MB_ICONERROR);
        return 1;
    }
}
