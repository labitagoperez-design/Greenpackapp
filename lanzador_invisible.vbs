Set WshShell = CreateObject("WScript.Shell")
' Forzamos la ruta exacta para que no de error 80070002
WshShell.CurrentDirectory = "Y:\Despacho\APP_GREENPACK"
WshShell.Run "cmd /c iniciar_greenpack.bat", 0, False