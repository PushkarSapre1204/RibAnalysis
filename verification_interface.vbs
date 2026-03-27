' Research Data Verification Tool Launcher
Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

strRootPath = "C:\Users\Pushkar\OneDrive - KTH\Thesis\RibAnalysis"
strBatPath = strRootPath & "\tools\verification_tool\launch_gui.bat"

If objFSO.FileExists(strBatPath) Then
    objShell.CurrentDirectory = strRootPath
    objShell.Run """" & strBatPath & """", 0, False
Else
    MsgBox "Error: launch_gui.bat not found at:" & vbCrLf & strBatPath, vbCritical, "File Not Found"
End If
