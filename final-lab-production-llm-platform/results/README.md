# Run evidence

This directory receives sanitized evidence only after an actual run. A run
folder should contain a metadata manifest, commands, raw request records,
metrics snapshot, server/router logs, and a concise summary. Generated CSV,
JSON and log artifacts are ignored by the root `.gitignore`; commit a reviewed
summary or an approved small fixture only when it contains no sensitive data.

No result is present in the initial scaffold.
