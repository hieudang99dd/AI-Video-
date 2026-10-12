Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)

venvPython = currentDir & "\.venv\Scripts\python.exe"
runPy = currentDir & "\run.py"

If fso.FileExists(venvPython) Then
    cmd = """" & venvPython & """ """ & runPy & """"
Else
    cmd = "python """ & runPy & """"
End If

WshShell.CurrentDirectory = currentDir
WshShell.Run cmd, 0, False
