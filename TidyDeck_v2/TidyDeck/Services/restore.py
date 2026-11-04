"""Point de restauration Windows — avec diagnostic précis de l'échec.

Causes fréquentes d'échec : pas de droits administrateur ; « Protection du système » désactivée
(c'est le cas par défaut sur beaucoup de PC) ; limite de 1 point / 24 h imposée par Windows
(contournée en réglant temporairement la valeur officielle SystemRestorePointCreationFrequency)."""
from Shared.Utils.common import IS_WINDOWS, is_admin, run_ps
from Shared.Utils.lang import T

SCRIPT = r'''
$ErrorActionPreference='Stop'
try {
  $k='HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\SystemRestore'
  $old=(Get-ItemProperty $k -Name SystemRestorePointCreationFrequency -ErrorAction SilentlyContinue).SystemRestorePointCreationFrequency
  Set-ItemProperty $k -Name SystemRestorePointCreationFrequency -Value 0 -Type DWord
  try { Checkpoint-Computer -Description '__DESC__' -RestorePointType MODIFY_SETTINGS -WarningAction Stop }
  finally {
    if ($old -eq $null) { Remove-ItemProperty $k -Name SystemRestorePointCreationFrequency -ErrorAction SilentlyContinue }
    else { Set-ItemProperty $k -Name SystemRestorePointCreationFrequency -Value $old -Type DWord }
  }
  $rp = Get-ComputerRestorePoint | Select-Object -Last 1
  if ($rp -and ((Get-Date) - [Management.ManagementDateTimeConverter]::ToDateTime($rp.CreationTime)).TotalMinutes -lt 10) { 'OK' } else { 'NOTFOUND' }
} catch { 'ERR:' + $_.Exception.Message }
'''
ENABLE = r'''$ErrorActionPreference='Stop'; try { Enable-ComputerRestore -Drive "$env:SystemDrive\"; 'OK' } catch { 'ERR:' + $_.Exception.Message }'''


def enable_protection():
    _, out = run_ps(ENABLE, 60)
    return out.strip().startswith("OK"), out.strip()


def create_restore_point(description="TidyDeck - avant modification", enable_if_needed=False):
    """Renvoie (ok, message, code) ; code : ok | admin | failed | other."""
    if not IS_WINDOWS:
        return False, "Disponible uniquement sous Windows.", "other"
    if not is_admin():
        return False, (T("Windows n'autorise la création d'un point de restauration qu'aux administrateurs. "
                       "Relance TidyDeck en administrateur.")), "admin"
    if enable_if_needed:
        enable_protection()
    _, out = run_ps(SCRIPT.replace("__DESC__", description.replace("'", "")), 240)
    out = out.strip()
    if out.startswith("OK"):
        return True, T("Point de restauration créé et vérifié."), "ok"
    if out.startswith("NOTFOUND"):
        return False, T("Windows a répondu sans erreur mais aucun point récent n'a été trouvé."), "failed"
    detail = out[4:].strip() if out.startswith("ERR:") else (out or T("pas de réponse de PowerShell"))
    return False, T("Windows a refusé : {v0}").format(v0=detail), "failed"
