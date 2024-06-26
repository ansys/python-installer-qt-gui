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

!define MULTIUSER_EXECUTIONLEVEL Highest
!define MULTIUSER_MUI
!define MULTIUSER_INSTALLMODE_COMMANDLINE
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
  ; Set the installation directory to the program files directory
  SetOutPath "$PROGRAMFILES64\ANSYS Inc\Ansys Python Manager"

  ; Copy the files from the dist\ansys_python_manager directory
  ; File /r /oname=ignore "dist\ansys_python_manager\*"
  File /r "dist\ansys_python_manager\*"

  ; Create the start menu directory
  CreateDirectory "$SMPROGRAMS\Ansys Python Manager"

  ; Create the start menu shortcut
  CreateShortCut "$SMPROGRAMS\Ansys Python Manager\Ansys Python Manager.lnk" "$INSTDIR\Ansys Python Manager.exe"

  ; Add the program to the installed programs list
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "UninstallString" "$\"$INSTDIR\uninstall.exe$\""
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "DisplayIcon" "$\"$INSTDIR\Ansys Python Manager.exe$\""
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "Publisher" "ANSYS Inc"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "Version" "${PRODUCT_VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "DisplayVersion" "${PRODUCT_VERSION}"

  WriteUninstaller "$INSTDIR\uninstall.exe"

SectionEnd

; Define the uninstaller section
Section "Uninstall" SEC02

  Delete "$PROGRAMFILES64\Ansys Python Manager\*.*"
  RMDir "$PROGRAMFILES64\Ansys Python Manager"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
  Delete "$SMPROGRAMS\Ansys Python Manager\Ansys Python Manager.lnk"
  RMDir "$SMPROGRAMS\Ansys Python Manager"
  Delete "$desktop\Ansys Python Manager.lnk"
SectionEnd

Icon "dist\ansys_python_manager\_internal\assets\pyansys_icon.ico"
InstallDir "$PROGRAMFILES64\ANSYS Inc\Ansys Python Manager"

; Define the custom functions for the MUI2 OneClick plugin
InstProgressFlags smooth
Function oneclickpre
  !insertmacro MUI_HEADER_TEXT "Installing ${PRODUCT_NAME}" "Please wait while the installation completes."
  ; !define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"
  HideWindow
FunctionEnd

; Call the MUI2 OneClick plugin
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE English
