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
    $doc.Close([ref]$false)
    Write-Host "PDF created successfully at: $pdfTarget"
} finally {
    if ($null -ne $word) {
        $word.Quit([ref]$false)
        [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
    }
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
}
