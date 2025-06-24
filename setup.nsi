; NSIS script for Ansys Python Manager installer

; Set the name, version, and output path of the installer
!define VERSION_FILE "src/ansys/tools/installer/VERSION"
!define LICENSE_FILE "LICENSE"
!define PRODUCT_NAME "Ansys Python Manager"
!define /file PRODUCT_VERSION "src/ansys/tools/installer/VERSION"
!define OUTFILE_NAME "Ansys-Python-Manager-Setup-v${PRODUCT_VERSION}.exe"

Name "${PRODUCT_NAME}"
VIProductVersion "${PRODUCT_VERSION}"
OutFile "dist\${OUTFILE_NAME}"

!define UNINSTKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\$(^Name)"
!define MULTIUSER_INSTALLMODE_DEFAULT_REGISTRY_KEY "${UNINSTKEY}"
!define MULTIUSER_INSTALLMODE_DEFAULT_REGISTRY_VALUENAME "CurrentUser"
!define MULTIUSER_INSTALLMODE_INSTDIR "ANSYS Inc\$(^Name)"
!define MULTIUSER_INSTALLMODE_COMMANDLINE
!define MULTIUSER_EXECUTIONLEVEL Highest
!define MULTIUSER_MUI

!include MultiUser.nsh
!include MUI2.nsh
!include InstallOptions.nsh

!define MUI_PAGE_CUSTOMFUNCTION_PRE oneclickpre
!insertmacro MULTIUSER_PAGE_INSTALLMODE
!insertmacro MUI_PAGE_LICENSE "${LICENSE_FILE}"
!insertmacro MUI_PAGE_INSTFILES
!include "uninstall.nsi"

Function CreateDesktopShortCut
  CreateShortCut "$desktop\Ansys Python Manager.lnk" "$INSTDIR\Ansys Python Manager.exe"
FunctionEnd

!define MUI_FINISHPAGE_RUN "$INSTDIR\Ansys Python Manager.exe"
!define MUI_FINISHPAGE_SHOWREADME
!define MUI_FINISHPAGE_SHOWREADME_TEXT "Create Desktop Shortcut"
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED
!define MUI_FINISHPAGE_SHOWREADME_FUNCTION "CreateDesktopShortCut"
!insertmacro MUI_PAGE_FINISH

Function .onInit
  !insertmacro MULTIUSER_INIT
FunctionEnd

Function un.onInit
  !insertmacro MULTIUSER_UNINIT
FunctionEnd

; Define the installer sections
Section "Ansys Python Manager" SEC01
  ; Set the installation directory dynamically based on user mode
  SetOutPath "$INSTDIR"

  ; Copy the files from the dist\ansys_python_manager directory
  File /r "dist\ansys_python_manager\*"

  ; Create the start menu directory
  CreateDirectory "$SMPROGRAMS\Ansys Python Manager"

  ; Create the start menu shortcut
  CreateShortCut "$SMPROGRAMS\Ansys Python Manager\Ansys Python Manager.lnk" "$INSTDIR\Ansys Python Manager.exe"

  ; Add the program to the installed programs list
  WriteRegStr SHCTX "${UNINSTKEY}" "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr SHCTX "${UNINSTKEY}" "UninstallString" "$INSTDIR\uninstall.exe"
  WriteRegStr SHCTX "${UNINSTKEY}" "DisplayIcon" "$INSTDIR\Ansys Python Manager.exe"
  WriteRegStr SHCTX "${UNINSTKEY}" "Publisher" "ANSYS Inc"
  WriteRegStr SHCTX "${UNINSTKEY}" "Version" "${PRODUCT_VERSION}"
  WriteRegStr SHCTX "${UNINSTKEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr ShCtx "${UNINSTKEY}" $MultiUser.InstallMode 1

  WriteUninstaller "$INSTDIR\uninstall.exe"

SectionEnd

Icon "dist\ansys_python_manager\_internal\assets\pyansys_icon.ico"

; Define the custom functions for the MUI2 OneClick plugin
InstProgressFlags smooth
Function oneclickpre
  !insertmacro MUI_HEADER_TEXT "Installing ${PRODUCT_NAME}" "Please wait while the installation completes."
  HideWindow
FunctionEnd

; Call the MUI2 OneClick plugin
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE English
