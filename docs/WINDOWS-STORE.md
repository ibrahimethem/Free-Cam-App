# Windows Store/MSIX feasibility

Assessment: October 18, 2026. This is a code/documentation assessment, **not** a
successful Store certification or a Windows runtime test. No MSIX has been
published and the working desktop/camera implementation has not been changed.

## Finding: the current full product cannot simply be repackaged

The host uses `MFCreateVirtualCamera` with a custom media-source CLSID. Windows
Frame Server loads that source in its own service process. `Setup.cpp` and
`windows.iss` currently install `NoSubCamera.dll` into an administrator-protected
Program Files directory and register its `InprocServer32` under HKLM. The
availability check in `Host.cpp` also reads that system-wide registration.

MSIX's private registry is not an equivalent replacement for that registration.
Microsoft documents limitations on exposing in-process COM modules outside a
package. Its own virtual-camera sample uses a separate MSI to install/register
the media source, even when the controlling application is packaged. Adding a
`com4:InProcessServer` manifest declaration alone is therefore not proof that
Frame Server can load this source.

References:

- https://learn.microsoft.com/en-us/windows/msix/desktop/desktop-to-uwp-prepare
- https://github.com/microsoft/Windows-Camera/blob/626f8b19c5f367602f2e89c6b314573d3776c9df/Samples/VirtualCamera/README.md
- https://learn.microsoft.com/en-us/uwp/schemas/appxpackage/uapmanifestschema/element-com4-inprocessserver
- https://learn.microsoft.com/en-us/windows/win32/api/mfvirtualcamera/nf-mfvirtualcamera-mfcreatevirtualcamera

## What free Store signing would and would not solve

Microsoft signs MSIX packages distributed through the Store. This does not
provide a general-purpose certificate for the separately installed camera DLL,
setup helper or an EXE installer downloaded from GitHub. Publishing an EXE/MSI
listing in the Store is not the same free-signing route.

A receiver-only MSIX could be investigated, but omitting native webcam output
or requiring a separately downloaded unsigned camera installer changes the
product/install experience. Do not silently ship such a reduced Store edition.
No claim is made that every possible future camera design is incompatible with
Store distribution; the current design has not demonstrated a self-contained,
Store-signed deployment path.

Reference: https://learn.microsoft.com/en-us/windows/apps/publish/faq/get-started-with-the-microsoft-store

## Fallback: explicitly unsigned public beta

The owner accepts an unsigned public beta as the fallback. Preserve the existing
working native camera and EXE installer rather than replace it with an unproven
MSIX. Before publication:

1. Audit the actual Windows bundle's third-party notices and corresponding-source
   obligations. Beta/unsigned status does not waive licenses. The Mac inventory
   must not be presented as a Windows audit.
2. Build the camera/application/installer on the Windows CI runner and run the
   existing hardware-free checks. Keep the production signed-release gate closed.
3. Label the asset, release notes and download button **unsigned public beta**;
   provide its source commit and SHA-256 checksum. Do not flip the site's current
   signed Windows `published` flag for an unsigned asset.
4. Explain that Windows security warnings or blocking may occur. Do not ask users
   to disable Defender, Smart App Control or signature enforcement, and do not
   install a self-signed root certificate as a public-distribution workaround.
5. Confirm a clean Windows 11 install and native webcam output before calling it
   a tested public beta. No such new test was performed during this assessment.

Reference: https://learn.microsoft.com/windows/apps/develop/smart-app-control/overview

SignPath Foundation declined the initial application according to the owner,
because the project needs an established usage/reputation history. Acceptance
is not pending and no signing request should be made using that application.
Reapplication may be considered after real public use; approval is not promised.
