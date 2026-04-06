Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = scriptDir

pythonwPath = shell.ExpandEnvironmentStrings("%LocalAppData%") & "\Programs\Python\Python313\pythonw.exe"
pythonPath = shell.ExpandEnvironmentStrings("%LocalAppData%") & "\Programs\Python\Python313\python.exe"
appPath = scriptDir & "\app_qt.py"
distPath = scriptDir & "\dist\quant_hunter\quant_hunter.exe"
distLatestPath = scriptDir & "\dist_latest\quant_hunter\quant_hunter.exe"

If fso.FileExists(pythonwPath) Then
    shell.Run "cmd /c cd /d """ & scriptDir & """ && start """" """ & pythonwPath & """ """ & appPath & """", 0, False
ElseIf fso.FileExists(pythonPath) Then
    shell.Run "cmd /c cd /d """ & scriptDir & """ && start """" """ & pythonPath & """ """ & appPath & """", 1, False
ElseIf fso.FileExists(distPath) Then
    shell.Run "cmd /c cd /d """ & scriptDir & """ && start """" """ & distPath & """", 1, False
ElseIf fso.FileExists(distLatestPath) Then
    shell.Run "cmd /c cd /d """ & scriptDir & """ && start """" """ & distLatestPath & """", 1, False
Else
    MsgBox "未找到可用启动方式，请先确认 Python 3.13 或程序文件存在。", 48, "量化猎手"
End If
