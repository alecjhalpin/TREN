# Real disposable Windows installer acceptance. Never run this on an end-user PC.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Drawing
$setup = (Get-ChildItem dist/VEYRA-Desktop-Setup-*.exe | Select-Object -First 1).FullName
$desktop = [Environment]::GetFolderPath('Desktop')
$program = Join-Path $env:LOCALAPPDATA 'Programs/VEYRA'
$legacy = Join-Path $env:LOCALAPPDATA 'Programs/TREN'
$link = Join-Path $desktop 'VEYRA.lnk'
$marker = Join-Path $env:APPDATA 'tren-desktop/installer-preservation.txt'
New-Item -ItemType Directory -Force (Split-Path $marker) | Out-Null
Set-Content $marker 'keep-profile-and-assistant-data'
function Assert($condition, $message) { if (-not $condition) { throw $message } }
function SilentInstall([string[]]$flags) {
  $p = Start-Process $setup -ArgumentList $flags -PassThru
  Assert ($p.WaitForExit(120000)) 'Installer timed out'
  Assert ($p.ExitCode -eq 0) "Installer exit code $($p.ExitCode)"
}
function Elements($root) { return $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition) }
function Wizard {
  $all = [System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children,[System.Windows.Automation.Condition]::TrueCondition)
  foreach ($e in $all) { if ($e.Current.Name -match '^VEYRA.*Setup|^VEYRA.*Installer') { return $e } }
  return $null
}
function Button($root,$pattern) {
  foreach ($e in (Elements $root)) { if ($e.Current.ControlType -eq [System.Windows.Automation.ControlType]::Button -and $e.Current.Name.Replace('&','') -match $pattern -and $e.Current.IsEnabled) { return $e } }
  return $null
}
# Walk the actual assisted installer and opt OUT using its visible checkbox.
$process = Start-Process $setup -PassThru
$end = [DateTime]::UtcNow.AddSeconds(45)
$checkbox = $null
while ([DateTime]::UtcNow -lt $end) {
  $window = Wizard
  if ($window) {
    foreach ($e in (Elements $window)) { if ($e.Current.Name -eq 'Create a desktop shortcut') { $checkbox=$e; break } }
    if ($checkbox) { break }
    $next = Button $window '^Next'
    if ($next) { $next.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke() }
  }
  Start-Sleep -Milliseconds 400
}
Assert ($null -ne $checkbox) 'Installer shortcut checkbox was not shown'
$toggle = $checkbox.GetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern)
Assert ($toggle.Current.ToggleState -eq [System.Windows.Automation.ToggleState]::On) 'Shortcut should default checked'
$folder = $null
foreach ($e in (Elements $window)) { if ($e.Current.ControlType -eq [System.Windows.Automation.ControlType]::Edit) { $folder=$e.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).Current.Value; break } }
Assert ($folder -eq $program) "Wrong default folder: $folder"
$bounds=$window.Current.BoundingRectangle
$bitmap=New-Object System.Drawing.Bitmap ([int]$bounds.Width),([int]$bounds.Height)
$graphics=[System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen([int]$bounds.Left,[int]$bounds.Top,0,0,$bitmap.Size)
$bitmap.Save((Join-Path (Get-Location) 'smoke-output/VEYRA-Installer-options.png'))
$graphics.Dispose();$bitmap.Dispose()
$toggle.Toggle()
Assert ($toggle.Current.ToggleState -eq [System.Windows.Automation.ToggleState]::Off) 'Cannot uncheck shortcut'
$next=Button $window '^(Next|Install)'
Assert ($null -ne $next) 'Install button missing'
$next.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
$end=[DateTime]::UtcNow.AddSeconds(120)
$finished=$false
while ([DateTime]::UtcNow -lt $end) {
  $window=Wizard
  if ($window) { $finish=Button $window '^Finish'; if ($finish) { $finish.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke();$finished=$true;break } }
  Start-Sleep -Milliseconds 500
}
Assert $finished 'Interactive install did not finish'
Assert (Test-Path (Join-Path $program 'TREN.exe')) 'Branded install folder missing app'
foreach ($module in @('playwright','kokoro-js','@huggingface/transformers','onnxruntime-node')) { Assert (Test-Path (Join-Path $program ('resources/tool-runtime/node_modules/'+$module+'/package.json'))) ('Packaged tool dependency missing: '+$module) }
Assert (Test-Path (Join-Path $program 'resources/node/node_modules/npm/bin/npm-cli.js')) 'Packaged npm missing'
Assert (Test-Path (Join-Path $program 'resources/backend/runtime/worker.mjs')) 'Packaged worker missing'
$env:VEYRA_TOOLS_ROOT = Join-Path $program 'resources/tool-runtime'
& (Join-Path $program 'resources/node/node.exe') --input-type=module -e "import {createRequire} from 'node:module';import {pathToFileURL} from 'node:url';const r=createRequire(process.env.VEYRA_TOOLS_ROOT+'/package.json');for(const n of ['playwright','onnxruntime-node','kokoro-js','@huggingface/transformers']){const m=await import(pathToFileURL(r.resolve(n)).href);if(!m)throw Error('Missing packaged module '+n)};console.log('Installed browser and native voice modules load successfully.')"
Assert ($LASTEXITCODE -eq 0) 'Installed native tool dependencies did not load'
Assert (-not (Test-Path $link)) 'Unchecked desktop shortcut was created'
# Silent updates preserve opt-out. Manual reinstalls can create/repair the shortcut.
SilentInstall @('/S','--updated')
Assert (-not (Test-Path $link)) 'Update recreated an opted-out shortcut'
SilentInstall @('/S')
Assert (Test-Path $link) 'Default desktop shortcut missing'
$shell=New-Object -ComObject WScript.Shell
Assert ($shell.CreateShortcut($link).TargetPath -eq (Join-Path $program 'TREN.exe')) 'Shortcut target wrong'
# Seed a legacy program folder and verify automatic update replacement plus opt-in startup.
SilentInstall @('/S',"/D=$legacy")
Assert (Test-Path (Join-Path $legacy 'TREN.exe')) 'Explicit directory not respected'
$run='HKCU:/Software/Microsoft/Windows/CurrentVersion/Run'
New-Item $run -Force | Out-Null
New-ItemProperty $run -Name 'tren-desktop' -Value ('"'+(Join-Path $legacy 'TREN.exe')+'"') -PropertyType String -Force | Out-Null
SilentInstall @('/S','--updated')
Assert (Test-Path (Join-Path $program 'TREN.exe')) 'Legacy folder was not upgraded to VEYRA'
Assert (-not (Test-Path (Join-Path $legacy 'TREN.exe'))) 'Old program installation still present'
Assert ($shell.CreateShortcut($link).TargetPath -eq (Join-Path $program 'TREN.exe')) 'Upgraded shortcut target wrong'
Assert ((Get-ItemPropertyValue $run 'tren-desktop') -eq ('"'+(Join-Path $program 'TREN.exe')+'"')) 'Sign-in launch target was not migrated'
Assert ((Get-Content $marker -Raw).Trim() -eq 'keep-profile-and-assistant-data') 'Profile was modified'
Write-Output 'Installer acceptance passed: visible options, default folder, opt-out, shortcut creation, legacy migration and profile/login preservation.'


# Exercise the installed application and its actual bundled dependencies.
$env:TREN_SMOKE_OUTPUT = Join-Path $PSScriptRoot 'smoke-output/installed'
Remove-Item Env:TREN_RESOURCES -ErrorAction SilentlyContinue
Remove-Item Env:TREN_DESKTOP_ROOT -ErrorAction SilentlyContinue
$p = Start-Process (Join-Path $program 'TREN.exe') -ArgumentList '--smoke-test' -PassThru
Assert ($p.WaitForExit(120000)) 'Installed app smoke timed out'
Assert ($p.ExitCode -eq 0) 'Installed app did not pass its real window smoke test'
