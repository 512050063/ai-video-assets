' AI Video Assets - hidden one-click launcher
' Double-click this file to start the LAN service with no console window.
' Also used by the Windows Scheduled Task for auto-start.
Option Explicit
Dim ws, fso, root, launcher
Set ws = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
launcher = root & "\service-run.bat"
If Not fso.FileExists(launcher) Then
    MsgBox "Launcher not found: " & launcher, 16, "AI Video Assets"
    WScript.Quit 1
End If
' 0 = hide window, False = do not wait
ws.Run """" & launcher & """", 0, False
