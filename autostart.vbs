' Legacy-compatible hidden launcher (kept for any existing shortcuts).
' Prefer "一键隐藏启动.bat" or the scheduled task.
Option Explicit
Dim ws, fso, root, launcher
Set ws = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
launcher = root & "\service-run.bat"
If fso.FileExists(launcher) Then ws.Run """" & launcher & """", 0, False
