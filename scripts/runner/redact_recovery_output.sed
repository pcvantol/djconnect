# Redact known secret-bearing patterns before recovery output reaches a log.
# Run with: sed -E -f redact_recovery_output.sed
s/((Authorization|authorization)[[:space:]]*:[[:space:]]*).*/\1[REDACTED]/g
s/(--(token|secret|password|authorization)[[:space:]]+)[^[:space:]]+/\1[REDACTED]/g
s/("[^"]*(token|Token|TOKEN|secret|Secret|SECRET|password|Password|PASSWORD|authorization|Authorization|AUTHORIZATION|credential|Credential|CREDENTIAL|private_key|PRIVATE_KEY)[^"]*"[[:space:]]*:[[:space:]]*")[^"]*/\1[REDACTED]/g
s/(([A-Za-z0-9_.-]*(token|Token|TOKEN|secret|Secret|SECRET|password|Password|PASSWORD|authorization|Authorization|AUTHORIZATION|credential|Credential|CREDENTIAL|private_key|PRIVATE_KEY)[A-Za-z0-9_.-]*)[[:space:]]*[:=][[:space:]]*)[^[:space:],;]+/\1[REDACTED]/g
s#(https?://[^/:[:space:]]+:)[^@[:space:]]+@#\1[REDACTED]@#g
s/(gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+)/[REDACTED]/g
