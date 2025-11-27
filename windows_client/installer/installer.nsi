; Managed Nebula Windows Client Installer
; NSIS Script for creating a single-file installer

!include "MUI2.nsh"
!include "nsDialogs.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"
!include "WordFunc.nsh"

; --------------------------------
; Preprocessor Macros (must be defined before use)
; --------------------------------

; String contains macro (used in PATH manipulation below)
!define StrContains "!insertmacro StrContains"
!macro StrContains ResultVar String SubString
  Push "${String}"
  Push "${SubString}"
  Call StrContains
  Pop "${ResultVar}"
!macroend

; --------------------------------
; General Configuration
; --------------------------------

!define PRODUCT_NAME "Managed Nebula"
!define PRODUCT_PUBLISHER "KumpeApps"
!define PRODUCT_WEB_SITE "https://github.com/kumpeapps/managed-nebula"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\NebulaAgentGUI.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

; Version will be set by build script
!ifndef VERSION
  !define VERSION "1.0.0"
!endif

Name "${PRODUCT_NAME} ${VERSION}"
OutFile "ManagedNebula-${VERSION}-Setup.exe"
InstallDir "$PROGRAMFILES\ManagedNebula"
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""
RequestExecutionLevel admin
ShowInstDetails show
ShowUnInstDetails show

; --------------------------------
; Interface Settings
; --------------------------------

!define MUI_ABORTWARNING
!define MUI_ICON "nebula.ico"
!define MUI_UNICON "nebula.ico"

; Welcome page
!define MUI_WELCOMEPAGE_TITLE "Welcome to ${PRODUCT_NAME} Setup"
!define MUI_WELCOMEPAGE_TEXT "This wizard will guide you through the installation of ${PRODUCT_NAME} ${VERSION}.$\r$\n$\r$\n${PRODUCT_NAME} is a Windows client for managing Nebula mesh VPN connections.$\r$\n$\r$\nClick Next to continue."

; Finish page
!define MUI_FINISHPAGE_RUN "$INSTDIR\NebulaAgentGUI.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${PRODUCT_NAME} GUI"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\README.md"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "View README"
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED  ; Uncheck README by default

; --------------------------------
; Pages
; --------------------------------

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; --------------------------------
; Languages
; --------------------------------

!insertmacro MUI_LANGUAGE "English"

; --------------------------------
; Installer Sections
; --------------------------------

Section "Main Application" SecMain
  SectionIn RO
  
  SetOutPath "$INSTDIR"
  SetOverwrite on
  
  ; Copy main executables
  File "NebulaAgent.exe"
  File "NebulaAgentService.exe"
  File "NebulaAgentGUI.exe"
  
  ; Copy Nebula binaries
  File "nebula.exe"
  File "nebula-cert.exe"
  ; Include Wintun driver DLL if available (non-fatal if missing)
  File /nonfatal "wintun.dll"
  
  ; Copy support files
  File "nebula.ico"
  File "README.md"
  File "agent.ini.example"
  
  ; Create ProgramData directory
  CreateDirectory "$COMMONFILES\..\ProgramData\Nebula"
  CreateDirectory "$COMMONFILES\..\ProgramData\Nebula\logs"
  
  ; Copy example config to ProgramData if not exists
  IfFileExists "$COMMONFILES\..\ProgramData\Nebula\agent.ini" +2 0
  CopyFiles /SILENT "$INSTDIR\agent.ini.example" "$COMMONFILES\..\ProgramData\Nebula\agent.ini"
  
  ; Create Start Menu shortcuts
  CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
  CreateShortcut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk" "$INSTDIR\NebulaAgentGUI.exe" "" "$INSTDIR\nebula.ico"
  CreateShortcut "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
  
  ; Create Desktop shortcut
  CreateShortcut "$DESKTOP\${PRODUCT_NAME}.lnk" "$INSTDIR\NebulaAgentGUI.exe" "" "$INSTDIR\nebula.ico"
  
  ; Write registry keys
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\NebulaAgentGUI.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\nebula.ico"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  
  ; Get installed size
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "EstimatedSize" "$0"
  
  ; Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Windows Service" SecService
  ; Install and start Windows Service
  DetailPrint "Installing Windows Service..."
  
  ; Stop service if running
  nsExec::ExecToLog 'sc stop NebulaAgent'
  Sleep 2000
  
  ; Delete existing service if exists
  nsExec::ExecToLog 'sc delete NebulaAgent'
  Sleep 1000
  
  ; Create the service
  nsExec::ExecToLog 'sc create NebulaAgent binPath= "$INSTDIR\NebulaAgentService.exe" start= auto DisplayName= "Managed Nebula Agent"'
  
  ; Set service description
  nsExec::ExecToLog 'sc description NebulaAgent "Managed Nebula VPN Agent - Polls server for configuration and manages the local Nebula daemon"'
  
  ; Configure service recovery options (restart on failure)
  nsExec::ExecToLog 'sc failure NebulaAgent reset= 86400 actions= restart/60000/restart/60000/restart/60000'
  
  DetailPrint "Windows Service installed successfully"
SectionEnd

Section "Add to PATH" SecPath
  ; Add installation directory to system PATH
  DetailPrint "Adding to system PATH..."
  
  ; Read current PATH
  ReadRegStr $0 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path"
  
  ; Check if already in PATH
  StrCpy $1 "$INSTDIR"
  ${StrContains} $2 $1 $0
  StrCmp $2 "" 0 PathExists
  
  ; Add to PATH
  WriteRegExpandStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path" "$0;$INSTDIR"
  
  ; Notify system of environment change
  SendMessage ${HWND_BROADCAST} ${WM_WININICHANGE} 0 "STR:Environment" /TIMEOUT=5000
  
  DetailPrint "Added to system PATH"
  Goto PathDone
  
PathExists:
  DetailPrint "Already in system PATH"
  
PathDone:
SectionEnd

; --------------------------------
; Section Descriptions
; --------------------------------

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} "Main application files including GUI, CLI, and Nebula binaries."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecService} "Install and configure Windows Service for automatic startup."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecPath} "Add installation directory to system PATH for command-line access."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; --------------------------------
; Uninstaller Section
; --------------------------------

Section "Uninstall"
  ; Stop and remove Windows Service
  DetailPrint "Stopping Windows Service..."
  nsExec::ExecToLog 'sc stop NebulaAgent'
  Sleep 2000
  
  DetailPrint "Removing Windows Service..."
  nsExec::ExecToLog 'sc delete NebulaAgent'
  Sleep 1000
  
  ; Stop any running Nebula processes
  nsExec::ExecToLog 'taskkill /IM nebula.exe /F'
  nsExec::ExecToLog 'taskkill /IM NebulaAgentGUI.exe /F'
  
  ; Remove installation directory
  Delete "$INSTDIR\NebulaAgent.exe"
  Delete "$INSTDIR\NebulaAgentService.exe"
  Delete "$INSTDIR\NebulaAgentGUI.exe"
  Delete "$INSTDIR\nebula.exe"
  Delete "$INSTDIR\nebula-cert.exe"
  Delete "$INSTDIR\nebula.ico"
  Delete "$INSTDIR\README.md"
  Delete "$INSTDIR\agent.ini.example"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  
  ; Remove shortcuts
  Delete "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk"
  Delete "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall.lnk"
  RMDir "$SMPROGRAMS\${PRODUCT_NAME}"
  Delete "$DESKTOP\${PRODUCT_NAME}.lnk"
  
  ; Remove registry keys
  DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"
  
  ; Remove from PATH
  ReadRegStr $0 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path"
  ${WordReplace} $0 ";$INSTDIR" "" "+" $1
  ${WordReplace} $1 "$INSTDIR;" "" "+" $2
  ${WordReplace} $2 "$INSTDIR" "" "+" $3
  WriteRegExpandStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path" "$3"
  
  ; Note: Don't remove ProgramData\Nebula to preserve configuration
  DetailPrint "Configuration preserved at C:\ProgramData\Nebula"
  DetailPrint "To remove all data, manually delete C:\ProgramData\Nebula"
  
  SetAutoClose false
SectionEnd

; --------------------------------
; Helper Functions
; --------------------------------

Function StrContains
  Exch $R1 ; SubString
  Exch
  Exch $R0 ; String
  Push $R2
  Push $R3
  Push $R4
  Push $R5
  StrLen $R2 $R0
  StrLen $R3 $R1
  StrCpy $R4 0
  
Loop:
  StrCpy $R5 $R0 $R3 $R4
  StrCmp $R5 $R1 Found
  IntOp $R4 $R4 + 1
  IntCmp $R4 $R2 0 Loop
  StrCpy $R0 ""
  Goto Done
  
Found:
  StrCpy $R0 $R1
  
Done:
  Pop $R5
  Pop $R4
  Pop $R3
  Pop $R2
  Pop $R1
  Exch $R0
FunctionEnd

; Initialize function
Function .onInit
  ; Check for admin rights
  UserInfo::GetAccountType
  Pop $0
  StrCmp $0 "Admin" +3 0
    MessageBox MB_OK|MB_ICONSTOP "Administrator privileges required to install ${PRODUCT_NAME}."
    Abort
FunctionEnd

Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Are you sure you want to uninstall ${PRODUCT_NAME}?" IDYES +2
    Abort
FunctionEnd
