; windows.nsi
; 
; This script creates a windows installer for the Fisheries Explorer using Nullsoft's NSIS
;

; Installer name
Name "Fisheries Explorer"
; Installer filename
OutFile "FisheriesExplorerInstall.exe"

; Default installation directory
InstallDir $PROGRAMFILES\FisheriesExplorer

; Directory prompt text
DirText "This will install the Fisheries Explorer. Please choose a directory for installation"


Section ""

; Include all the actual files
SetOutPath $INSTDIR
File /r dist\*.*



; Start menu shortcut
CreateShortCut "$SMPROGRAMS\Fisheries Explorer.lnk" "$INSTDIR\fisheries_gui.exe"
; Desktop shortcut
CreateShortCut "$DESKTOP\Fisheries Explorer.lnk" "$INSTDIR\fisheries_gui.exe"

; Write uninstall information to the registry
WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Fisheries Explorer" "DisplayName" "Fisheries Explorer (remove only)"
WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Fisheries Explorer" "UninstallString" "$INSTDIR\Uninstall.exe"

;Create the uninstaller
WriteUninstaller $INSTDIR\Uninstall.exe
  
;Exec "$INSTDIR\dbUpgrader.exe"  ; this would run a post-install program you provided
SectionEnd

; Uninstaller setup

Section "Uninstall"

; Remove installed files
RMDir /R $INSTDIR

; Remove links
Delete "$SMPROGRAMS\Fisheries Explorer.lnk"
Delete "$DESKTOP\Fisheries Explorer.lnk"

; Remove uninstall registry entry
DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Fisheries Explorer"

SectionEnd