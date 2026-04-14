[Version]
Class=IEXPRESS
SEDVersion=3

[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=1
HideExtractAnimation=1
UseLongFileName=1
InsideCompressed=1
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=%InstallPrompt%
DisplayLicense=%DisplayLicense%
FinishMessage=%FinishMessage%
TargetName=%TargetName%
FriendlyName=%FriendlyName%
AppLaunched=%AppLaunched%
PostInstallCmd=%PostInstallCmd%
AdminQuietInstCmd=%AdminQuietInstCmd%
UserQuietInstCmd=%UserQuietInstCmd%
SourceFiles=SourceFiles

[Strings]
InstallPrompt=
DisplayLicense=
FinishMessage=Quant Hunter installation is complete.
TargetName=C:\Users\18335\DOCUME~1\NEWPRO~1\releases\quant_hunter_setup_20260414_154643.exe
FriendlyName=Quant Hunter Installer
AppLaunched=cmd /c install_quant_hunter.cmd
PostInstallCmd=<None>
AdminQuietInstCmd=cmd /c install_quant_hunter.cmd
UserQuietInstCmd=cmd /c install_quant_hunter.cmd
FILE0="install_quant_hunter.cmd"
FILE1="quant_hunter_portable.zip"
FILE2="README.txt"

[SourceFiles]
SourceFiles0=C:\Users\18335\DOCUME~1\NEWPRO~1\.installer_build\

[SourceFiles0]
%FILE0%=
%FILE1%=
%FILE2%=
