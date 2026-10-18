Option Explicit
On Error Resume Next

Dim WshShell, fso, scriptDir, pythonwExe, mainPy, cmd

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonwExe = scriptDir & "\.venv\Scripts\pythonw.exe"
mainPy = scriptDir & "\main.py"

WshShell.CurrentDirectory = scriptDir

If fso.FileExists(pythonwExe) Then
    cmd = Chr(34) & pythonwExe & Chr(34) & " " & Chr(34) & mainPy & Chr(34)
    WshShell.Run cmd, 1, False
Else
    WshShell.Run "cmd /c uv run pythonw main.py", 0, False
End If

If Err.Number <> 0 Then
    MsgBox "Lỗi khởi động: " & Err.Description, vbCritical, "ScreenRecorder Pro"
End If

Set WshShell = Nothing
Set fso = Nothing
