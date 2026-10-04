param(
    [string]$docxPath = "$PSScriptRoot\..\BaoCao_KyThuat_POC_Nhom4_OlaSM.docx",
    [string]$pdfPath = "$PSScriptRoot\..\BaoCao_KyThuat_POC_Nhom4_OlaSM.pdf"
)

$docxResolved = (Resolve-Path $docxPath).Path
$pdfTarget = [System.IO.Path]::GetFullPath($pdfPath)

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($docxResolved, $false, $true)
    $wdFormatPDF = 17
    $doc.SaveAs($pdfTarget, $wdFormatPDF)
    $doc.Close(0)
    Write-Host "PDF created successfully at: $pdfTarget"
} finally {
    $word.Quit(0)
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
}
