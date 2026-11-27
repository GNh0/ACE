# Run this yourself in your own terminal. It asks for the Console API key with hidden input and stores it in a
# Windows user environment variable (default ANTHROPIC_CREDIT_KEY; -Name to change it, and set the same name as
# "anthropic_key_var" in ~/.claude/ace/credit.json). Nothing is printed or written to a file.
param([string]$Name = "ANTHROPIC_CREDIT_KEY")
$secure = Read-Host -AsSecureString "Claude Console API key (input hidden)"
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    if (-not $plain.StartsWith("sk-ant-")) { Write-Host "Not an Anthropic API key (should start with sk-ant-). Nothing saved."; exit 1 }
    [Environment]::SetEnvironmentVariable($Name, $plain, "User")
    Write-Host "Saved to the user environment variable $Name."
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    Remove-Variable plain -ErrorAction SilentlyContinue
}
python -B "$PSScriptRoot\credit_run.py" status
