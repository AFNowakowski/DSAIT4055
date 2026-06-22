$inFile   = './in.sql'
$csvFile  = './comment_labels.csv'
$outFile  = './out-runme.sql'

$rows   = [System.Collections.Generic.List[string]]::new()
$lineNo = 0

foreach ($line in Get-Content $inFile) {
    $lineNo++
    if ([string]::IsNullOrWhiteSpace($line)) { continue }

    if ($line -notmatch 'VALUES\s*\(\s*(\d+).*,\s*([^,)]+)\)\s*;\s*$') {
        throw "Line ${lineNo}: does not match expected INSERT pattern -> $line"
    }

    $id    = $matches[1]
    $value = $matches[2].Trim()

    if ($value -ne '0' -and $value -ne '1') {
        throw "Line ${lineNo}: hl_IndicatedDeprecation must be 0 or 1 but was '$value' -> $line"
    }

    $rows.Add("$id,$value")
}

# Write CSV (no header -> nothing to IGNORE on load)
$rows | Set-Content $csvFile -Encoding UTF8

# MySQL wants forward slashes even on Windows; LOCAL INFILE resolves client-side,
# so give it an absolute path.
$csvPath = (Resolve-Path $csvFile).Path -replace '\\', '/'

$sql = @"
SET autocommit = 0;
SET unique_checks = 0;
SET GLOBAL local_infile = 1;

CREATE TEMPORARY TABLE _comment_labels (
    id    BIGINT      NOT NULL PRIMARY KEY,
    value TINYINT     NOT NULL
);

LOAD DATA LOCAL INFILE '$csvPath'
INTO TABLE _comment_labels
FIELDS TERMINATED BY ','
LINES TERMINATED BY '\n'
(id, value);

UPDATE Comments c
JOIN _comment_labels s ON c.Id = s.id
SET c.hl_IndicatedDeprecation = s.value;

COMMIT;

SET GLOBAL local_infile = 0;
DROP TEMPORARY TABLE _comment_labels;
"@

$sql | Set-Content $outFile -Encoding UTF8
Write-Host "Wrote $($rows.Count) rows to $csvFile and loader to $outFile"