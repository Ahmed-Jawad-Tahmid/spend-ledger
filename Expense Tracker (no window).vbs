' Launches the expense tracker with no console window.
' To stop it later: Task Manager -> find "pythonw.exe" -> End task.
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = fso.GetParentFolderName(WScript.ScriptFullName)
sh.Run "pythonw app.py", 0, False
