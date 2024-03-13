; Uninstaller script for Ansys Python Manager

; Name and version of the program to be uninstalled are already defined

Var DeleteDefaultVenvPath
Var DeleteConfiguration

; Define the uninstaller section
Section "Uninstall"
  ; Prompt the user to confirm uninstallation
  MessageBox MB_YESNO|MB_ICONQUESTION "Are you sure you want to uninstall ${PRODUCT_NAME} ${PRODUCT_VERSION}?" /SD IDYES IDYES +2
  Abort

  MessageBox MB_YESNO "Do you want to delete the contents in the default virtual environment path location?" IDYES +2
  StrCpy $DeleteDefaultVenvPath 1
+2:
  MessageBox MB_YESNO "Do you want to delete the Ansys Python Manager stored configuration?" IDYES +2
  StrCpy $DeleteConfiguration 1
+2:

  ; Get the user's profile directory
  ReadEnvStr $0 "PROFILE"

  ; Delete directories if required
  ${If} $DeleteDefaultVenvPath == 1
      RMDir /r "$0\.ansys_python_venvs"
  ${EndIf}
  ${If} $DeleteConfiguration == 1
      RMDir /r "$0\.ansys"
  ${EndIf}

  ; Remove the installed files
  Delete "$INSTDIR\*.*"
  RMDir /r /REBOOTOK "$INSTDIR"

  ; Remove the registry keys
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"

  ; Remove the start menu shortcut and directory
  Delete "$SMPROGRAMS\Ansys Python Manager\Ansys Python Manager.lnk"
  RMDir /r /REBOOTOK "$SMPROGRAMS\Ansys Python Manager"

  ; Display the uninstallation complete message
  MessageBox MB_OK|MB_ICONINFORMATION "${PRODUCT_NAME} ${PRODUCT_VERSION} has been successfully uninstalled."
SectionEnd
