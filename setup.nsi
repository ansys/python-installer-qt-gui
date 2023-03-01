; NSIS script for Ansys Python Manager installer


; Set the name, version, and output path of the installer
!define PRODUCT_NAME "Ansys Python Manager"
!define PRODUCT_VERSION "0.1.0-beta0"
!define OUTFILE_NAME "Ansys Python Manager Setup-v${PRODUCT_VERSION}.exe"
Name "${PRODUCT_NAME}"
VIProductVersion "${PRODUCT_VERSION}"
OutFile "dist\${OUTFILE_NAME}"

; Define the installer sections
Section "Ansys Python Manager" SEC01
  ; Set the installation directory to the program files directory
  SetOutPath "$PROGRAMFILES64\ANSYS Inc\Ansys Python Manager"
  
  ; Copy the files from the dist\ansys_python_manager directory
  File /r "dist\ansys_python_manager\*"
  
  ; Create the start menu directory
  CreateDirectory "$SMPROGRAMS\Ansys Python Manager"
  
  ; Create the start menu shortcut
  CreateShortCut "$SMPROGRAMS\Ansys Python Manager\Ansys Python Manager.lnk" "$INSTDIR\Ansys Python Manager.exe"
SectionEnd

; Define the uninstaller section
Section "Uninstall" SEC02
  ; Remove the installed files
  Delete "$PROGRAMFILES64\Ansys Python Manager\*.*"
  RMDir "$PROGRAMFILES64\Ansys Python Manager"

  ; Remove the registry keys
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ansys Python Manager"
  
  ; Remove the start menu shortcut and directory
  Delete "$SMPROGRAMS\Ansys Python Manager\Ansys Python Manager.lnk"
  RMDir "$SMPROGRAMS\Ansys Python Manager"
SectionEnd

; Set the installer properties
Name "${PRODUCT_NAME}"
Icon "dist\ansys_python_manager\assets\pyansys_icon.ico"
InstallDir "$PROGRAMFILES64\ANSYS Inc\Ansys Python Manager"

; Simplify the installer GUI
InstProgressFlags smooth
