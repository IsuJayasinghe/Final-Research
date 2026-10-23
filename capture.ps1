$browser = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
$pages = @(
    @{ file = 'dashboard.html'; out = '01_operations_dashboard.png' },
    @{ file = 'task-assignment.html'; out = '02_task_assignment.png' },
    @{ file = 'live-tracking.html'; out = '03_live_tracking.png' },
    @{ file = 'task-management.html'; out = '04_task_management.png' },
    @{ file = 'analytics.html'; out = '05_performance_analytics.png' }
)

foreach ($p in $pages) {
    $outFile = Join-Path 'D:\AI_port_management\screenshots' $p.out
    $url = "file:///D:/AI_port_management/$($p.file)"
    Write-Host "Capturing $($p.file) to $($p.out)..."
    $proc = Start-Process -FilePath $browser -ArgumentList "--headless", "--screenshot=$outFile", "--window-size=1280,860", "--hide-scrollbars", $url -PassThru -Wait
}

Write-Host "Done capturing all 5 pages."
Get-ChildItem 'D:\AI_port_management\screenshots' | Select-Object Name, Length
