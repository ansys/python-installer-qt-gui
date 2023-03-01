; NSIS script for Ansys Python Manager installer

; Set the name and output path of the installer
Name "Ansys Python Manager"
OutFile "AnsysPythonManagerInstaller.exe"

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
Name "Ansys Python Manager"
Icon "dist\ansys_python_manager\assets\pyansys_icon.ico"
InstallDir "$PROGRAMFILES64\ANSYS Inc\Ansys Python Manager"




; ; NSIS script for Ansys Python Manager installer

; ; Set the name and output path of the installer
; Name "Ansys Python Manager"
; OutFile "AnsysPythonManagerInstaller.exe"

; ; Define the installer sections
; Section "Ansys Python Manager" SEC01
;   ; Set the installation directory to the program files directory
;   SetOutPath "$PROGRAMFILES64\ANSYS Inc\Ansys Python Manager"
  
;   ; Copy the files from the dist\ansys_python_manager directory
;   File /r "dist\ansys_python_manager\*"
; SectionEnd

; ; Define the uninstaller section
; Section "Uninstall" SEC02
;   ; Remove the installed files
;   Delete "$PROGRAMFILES64\Ansys Python Manager\*.*"
;   RMDir "$PROGRAMFILES64\Ansys Python Manager"

;   ; Remove the registry keys
;   DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ansys Python Manager"
; SectionEnd

; ; Define the installer attributes
; !define MUI_ICON "dist\ansys_python_manager\assets\pyansys_icon.ico"
; ; !define MUI_UNICON "dist\ansys_python_manager\Ansys Python Manager.exe"
; ; !insertmacro MUI_PAGE_DIRECTORY
; ; !insertmacro MUI_PAGE_INSTFILES
; ; !insertmacro MUI_LANGUAGE "English"

; ; Set the installer properties
; Name "${PRODUCT_NAME}"
; Icon "${MUI_ICON}"
; ; UninstallIcon "${MUI_UNICON}"
; InstallDir "$PROGRAMFILES64\ANSYS Inc\Ansys Python Manager"
; ; UninstallDisplayName "${PRODUCT_NAME}"
; ; UninstallDisplayIcon "${MUI_UNICON}"
