param([Parameter(Mandatory)][string]$SchemaFile, [Parameter(Mandatory)][string]$CatalogFile)
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$rootSchema = Get-Content -LiteralPath $SchemaFile -Raw | ConvertFrom-Json -AsHashtable -Depth 100
$catalog = Get-Content -LiteralPath $CatalogFile -Raw | ConvertFrom-Json -AsHashtable -Depth 100
$defs = @{}
foreach ($entry in $rootSchema['$defs'].GetEnumerator()) { $defs[$entry.Key] = $entry.Value }
foreach ($entry in $catalog.types.GetEnumerator()) { $defs[$entry.Key] = $entry.Value }
while ($null -ne ($line = [Console]::ReadLine())) {
    try {
        $request = $line | ConvertFrom-Json -AsHashtable -Depth 100
        $selected = $rootSchema
        if ($request.ContainsKey('schema')) {
            $selected = @{ '$schema'='https://json-schema.org/draft/2020-12/schema'; '$defs'=$defs }
            foreach ($entry in $request.schema.GetEnumerator()) { $selected[$entry.Key]=$entry.Value }
        }
        $validationErrors = @()
        $valid = Test-Json -Json (ConvertTo-Json -InputObject $request.value -Depth 100 -Compress) -Schema ($selected | ConvertTo-Json -Depth 100 -Compress) -ErrorAction SilentlyContinue -ErrorVariable validationErrors
        $reply = @{ valid=[bool]$valid; errors=@($validationErrors | ForEach-Object { $_.ToString() }); version=$PSVersionTable.PSVersion.ToString() }
    } catch {
        $reply = @{ valid=$false; errors=@($_.Exception.Message); version=$PSVersionTable.PSVersion.ToString() }
    }
    [Console]::WriteLine(($reply | ConvertTo-Json -Depth 10 -Compress))
    [Console]::Out.Flush()
}

