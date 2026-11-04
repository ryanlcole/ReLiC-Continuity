# Security policy

This is experimental local-first code; **not production certified**. It has no remote authentication or internet-facing service and stores event metadata on the local filesystem. Its SQLite triggers and SHA-256 chain help detect some mutations, but a privileged user can alter the database, triggers and hashes; local time is not independently attested. Avoid secrets, company data and personal information.

Report suspected vulnerabilities privately to the repository maintainers through GitHub private vulnerability reporting when the public repository is live. Do not publish exploits or customer data in issues. The maintainers should review the GitHub security settings before accepting outside reports.
