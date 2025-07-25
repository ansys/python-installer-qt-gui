; Uninstaller script for Ansys Python Manager

; Name and version of the program to be uninstalled are already defined

Var DeleteDefaultVenvPath
Var DeleteConfiguration

; Define the uninstaller section
Section "Uninstall"
  MessageBox MB_YESNO|MB_ICONQUESTION "Do you want to delete the contents in the default virtual environment path location?" IDYES deleteVenvPath
  StrCpy $DeleteDefaultVenvPath 0
  Goto checkDeleteConfiguration

deleteVenvPath:
  StrCpy $DeleteDefaultVenvPath 1
  Goto checkDeleteConfiguration

checkDeleteConfiguration:
  MessageBox MB_YESNO|MB_ICONQUESTION "Do you want to delete the Ansys Python Manager stored configuration?" IDYES deleteConfiguration
  StrCpy $DeleteConfiguration 0
  Goto doneAsking

deleteConfiguration:
  StrCpy $DeleteConfiguration 1
  Goto doneAsking

doneAsking:
  !include LogicLib.nsh
  ; Echo the values of $DeleteConfiguration and $DeleteDefaultVenvPath
  DetailPrint "User home: $PROFILE"
  DetailPrint "DeleteConfiguration: $DeleteConfiguration"
  DetailPrint "DeleteDefaultVenvPath: $DeleteDefaultVenvPath"


  ; Delete directories if required
  ${If} $DeleteDefaultVenvPath == 1
      RMDir /r "$PROFILE\.ansys_python_venvs"
  ${EndIf}
  ${If} $DeleteConfiguration == 1
      RMDir /r "$PROFILE\.ansys\ansys_python_manager"
  ${EndIf}

  ; Remove the installed files
  Delete "$INSTDIR\*.*"
  RMDir /r /REBOOTOK "$INSTDIR"

  ; Remove the registry keys
  DetailPrint "${UNINSTKEY}"
  DeleteRegKey SHCTX "${UNINSTKEY}"

  ; Remove the start menu shortcut and directory
  Delete "$SMPROGRAMS\Ansys Python Manager\Ansys Python Manager.lnk"
  RMDir /r /REBOOTOK "$SMPROGRAMS\Ansys Python Manager"

  ; Remove the desktop shortcut
  Delete "$desktop\Ansys Python Manager.lnk"

  ; Display the uninstallation complete message
  MessageBox MB_OK|MB_ICONINFORMATION "${PRODUCT_NAME} ${PRODUCT_VERSION} has been successfully uninstalled."
SectionEnd
