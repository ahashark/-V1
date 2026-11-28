<#
.SYNOPSIS
  Windows 本地一键上传发布包并远程部署至 Ubuntu 虚拟机 (192.168.118.128)

.EXAMPLE
  .\deploy\upload_and_deploy.ps1 -User ubuntu
  .\deploy\upload_and_deploy.ps1 -User root -Port 80 -Mode full
  .\deploy\upload_and_deploy.ps1 -User root -Mode static
#>
param(
    [string]$ServerIp = "192.168.118.128",
    [string]$User = "xh",
    [int]$Port = 80,
    [ValidateSet("full", "static")]
    [string]$Mode = "full"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ArchivePath = Join-Path $ProjectRoot "dist\atelier-fragrance-ubuntu-release.tar.gz"

if (-not (Test-Path $ArchivePath)) {
    Write-Host "[INFO] 未检测到发布包，正在先执行编译打包..." -ForegroundColor Cyan
    $VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (Test-Path $VenvPython) {
        & $VenvPython (Join-Path $ProjectRoot "build_release.py")
    } else {
        python (Join-Path $ProjectRoot "build_release.py")
    }
}

$RemoteTar = "~/atelier-fragrance-ubuntu-release.tar.gz"
$RemoteDir = "/tmp/atelier-fragrance-release"

Write-Host "==========================================================" -ForegroundColor Green
Write-Host " 正在上传发布包至 ${User}@${ServerIp}:${RemoteTar}" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
scp $ArchivePath "${User}@${ServerIp}:${RemoteTar}"
if ($LASTEXITCODE -ne 0) {
    throw "SCP 上传失败，请确认虚拟机 ${ServerIp} 已开启 SSH 服务且用户名正确。"
}

Write-Host "==========================================================" -ForegroundColor Green
Write-Host " 正在远程解压并执行自动化部署脚本 (模式: $Mode, 端口: $Port)..." -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
$RemoteCmd = "sudo rm -rf $RemoteDir && mkdir -p $RemoteDir && tar -xzf $RemoteTar -C $RemoteDir --strip-components=1 && sudo bash $RemoteDir/deploy_ubuntu.sh --host $ServerIp --port $Port --mode $Mode"
ssh -t "${User}@${ServerIp}" $RemoteCmd
if ($LASTEXITCODE -ne 0) {
    throw "远程部署执行失败，请检查上方终端日志。"
}

$PortSuffix = if ($Port -eq 80) { "" } else { ":$Port" }
Write-Host ""
Write-Host "[DONE] 远程发布完成！请在浏览器打开: http://${ServerIp}${PortSuffix}" -ForegroundColor Cyan
