# Security

## What jsrecon does and doesn't do

- It downloads the same JavaScript a browser downloads on a normal page load (plus the source
  maps those scripts reference) and analyses it locally.
- It sends an honest `User-Agent: jsrecon/<version> (+https://github.com/web3daemon/jsrecon)`.
- It does not log in, replay requests, call the endpoints it finds, bypass bot protection or
  rate limits, or hide its traffic.
- The secret scan looks for server credentials that should never be in a client bundle.
  Values are masked in every output (`AKIA…LE (20 chars)`); jsrecon never stores or sends them.

## Using it responsibly

Point it at your own apps, public APIs, and systems you are authorised to test (for bug bounty:
within the program's scope). If you find a live credential in someone else's bundle, report it
to the owner through their security contact or bug-bounty program — don't use it.

## Reporting a vulnerability in jsrecon

Open a [private security advisory](https://github.com/web3daemon/jsrecon/security/advisories/new)
on GitHub. Please don't file public issues for security problems.

`sourcemaps.write_originals` is the one place where untrusted input decides file paths; paths
are normalised so a map can't write outside the output directory (`../../` is stripped). Reports
of a way around that are especially welcome.
