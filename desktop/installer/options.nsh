; Keep the legacy executable/appId/profile while branding the program folder independently.
!undef APP_FILENAME
!define APP_FILENAME "VEYRA"
!include nsDialogs.nsh
!include FileFunc.nsh

!ifndef BUILD_UNINSTALLER
Var VeyraOptionsDialog
Var VeyraFolderInput
Var VeyraShortcutCheckbox
Var VeyraCreateShortcut
Var VeyraPreviousInstallDir
Var VeyraExplicitDir


; Defer plugin-using functions until electron-builder has registered all plugin directories.
!macro customHeader
Function VeyraNormalizeFolder
  ${If} $VeyraExplicitDir != ""
    Return
  ${EndIf}
  ; Rename only the legacy app folder leaf; keep its parent and custom non-TREN paths.
  ${GetFileName} "$INSTDIR" $0
  ${If} $0 == "TREN"
    ${GetParent} "$INSTDIR" $1
    StrCpy $INSTDIR "$1\VEYRA"
  ${EndIf}
FunctionEnd
Function VeyraInstallOptions
  ; Install-mode selection can restore the previous registry path; normalize it here too.
  Call VeyraNormalizeFolder
  ${If} ${isUpdated}
    Abort
  ${EndIf}
  !insertmacro MUI_HEADER_TEXT "Install VEYRA" "Choose where to install VEYRA and whether to create a desktop shortcut."
  nsDialogs::Create 1018
  Pop $VeyraOptionsDialog
  ${If} $VeyraOptionsDialog == error
    Abort
  ${EndIf}
  ${NSD_CreateLabel} 0u 8u 100% 18u "Installation folder"
  Pop $0
  ${NSD_CreateText} 0u 30u 78% 14u "$INSTDIR"
  Pop $VeyraFolderInput
  ${NSD_CreateBrowseButton} 80% 29u 20% 16u "Browse…"
  Pop $0
  ${NSD_OnClick} $0 VeyraBrowseFolder
  ${NSD_CreateCheckbox} 0u 65u 100% 16u "Create a desktop shortcut"
  Pop $VeyraShortcutCheckbox
  ${NSD_SetState} $VeyraShortcutCheckbox $VeyraCreateShortcut
  ${NSD_CreateLabel} 0u 98u 100% 35u "Your existing assistant name, conversations and connections are kept in their current data folder."
  Pop $0
  nsDialogs::Show
FunctionEnd
Function VeyraBrowseFolder
  Pop $0
  ${NSD_GetText} $VeyraFolderInput $1
  nsDialogs::SelectFolderDialog "Choose the VEYRA installation folder" "$1"
  Pop $0
  ${If} $0 != error
    ${NSD_SetText} $VeyraFolderInput "$0"
  ${EndIf}
FunctionEnd
Function VeyraInstallOptionsLeave
  ${NSD_GetText} $VeyraFolderInput $INSTDIR
  ${If} $INSTDIR == ""
    MessageBox MB_OK|MB_ICONEXCLAMATION "Choose an installation folder."
    Abort
  ${EndIf}
  ${NSD_GetState} $VeyraShortcutCheckbox $VeyraCreateShortcut
FunctionEnd
!macroend

!macro customInit
  !insertmacro GetDParameter $VeyraExplicitDir
  StrCpy $VeyraPreviousInstallDir "$INSTDIR"
  StrCpy $VeyraCreateShortcut ${BST_CHECKED}
  ${If} ${isNoDesktopShortcut}
    StrCpy $VeyraCreateShortcut ${BST_UNCHECKED}
  ${EndIf}
  ; Silent updates retain the user's choice about having a desktop shortcut.
  ${If} ${isUpdated}
    StrCpy $VeyraCreateShortcut ${BST_UNCHECKED}
    ${If} ${FileExists} "$DESKTOP\VEYRA.lnk"
    ${OrIf} ${FileExists} "$DESKTOP\TREN.lnk"
      StrCpy $VeyraCreateShortcut ${BST_CHECKED}
    ${EndIf}
  ${EndIf}
  Call VeyraNormalizeFolder
!macroend

!macro customPageAfterChangeDir
  Page custom VeyraInstallOptions VeyraInstallOptionsLeave
!macroend




!macro customInstall
  ; Start menu links still use the maintained electron-builder implementation.
  ${If} $VeyraCreateShortcut == ${BST_CHECKED}
    CreateShortCut "$DESKTOP\VEYRA.lnk" "$appExe" "" "$appExe" 0 "" "" "${APP_DESCRIPTION}"
    WinShell::SetLnkAUMI "$DESKTOP\VEYRA.lnk" "${APP_ID}"
  ${Else}
    Delete "$DESKTOP\VEYRA.lnk"
  ${EndIf}
  ; The old installer already removes its old link; cover the recorded legacy name too.
  ${If} $oldShortcutName == "TREN"
    Delete "$oldDesktopLink"
  ${EndIf}
  ; Preserve opt-in login launch when migrating the old program folder.
  !insertmacro VeyraUpdateLoginEntry "tren-desktop"
  !insertmacro VeyraUpdateLoginEntry "TREN"
!macroend

!macro VeyraUpdateLoginEntry NAME
  ReadRegStr $0 HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "${NAME}"
  ${If} $0 == '$\"$VeyraPreviousInstallDir\TREN.exe$\"'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "${NAME}" '$\"$appExe$\"'
  ${EndIf}
!macroend
!else
!macro customUnInstall
  ${IfNot} ${isUpdated}
    Delete "$DESKTOP\VEYRA.lnk"
  ${EndIf}
!macroend
!endif
