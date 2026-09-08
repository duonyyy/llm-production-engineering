# Failure-injection boundary

Failure drills validate declared behaviour, not just error logging. They may be
run only in an environment where the target can be safely interrupted. No
failure scenario is marked passed until its command, observed result, relevant
correlation IDs and cleanup result are retained under `results/`.
