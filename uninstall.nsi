; Uninstaller script for Ansys Python Manager

; Name and version of the program to be uninstalled are already defined


; Define the uninstaller section
Section "Uninstall"
  ; Prompt the user to confirm uninstallation
  MessageBox MB_YESNO|MB_ICONQUESTION "Are you sure you want to uninstall ${PRODUCT_NAME} ${PRODUCT_VERSION}?" /SD IDYES IDYES +2
  Abort

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
