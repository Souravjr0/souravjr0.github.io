$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$externalDir = Join-Path $projectDir "external"

New-Item -ItemType Directory -Force -Path $externalDir | Out-Null

$repos = @(
    @{ Name = "investing-algorithm-framework"; Url = "https://github.com/coding-kitties/investing-algorithm-framework.git" },
    @{ Name = "trading-bot-framework"; Url = "https://github.com/pecan987/trading-bot-framework.git" },
    @{ Name = "AlgorithmicTradingEngine"; Url = "https://github.com/JohannesMeyerYC/AlgorithmicTradingEngine.git" },
    @{ Name = "Advanced_AI_ML_Trading_Framework"; Url = "https://github.com/CodingEye/Advanced_AI_ML_Trading_Framework.git" },
    @{ Name = "delta-riskbot"; Url = "https://github.com/rickymagal/delta-riskbot.git" },
    @{ Name = "nautilus_trader"; Url = "https://github.com/nautechsystems/nautilus_trader.git" },
    @{ Name = "quant"; Url = "https://github.com/AryaaSk/quant.git" },
    @{ Name = "ai-trading-platform"; Url = "https://github.com/gregorizeidler/ai-trading-platform.git" }
)

foreach ($repo in $repos) {
    $dest = Join-Path $externalDir $repo.Name
    if (Test-Path $dest) {
        Write-Host "Skipping $($repo.Name): already exists."
        continue
    }
    git clone $repo.Url $dest
}

Write-Host "Done. Set entrypoints in .env and run: python external_frameworks.py list"
