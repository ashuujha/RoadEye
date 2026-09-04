# Security boundaries

Local synthetic demonstration only. Development authentication/demo controls require explicit configuration; unsupported real source modes fail at startup. Local password is generated into ignored `.env`, never compiled into the browser. Four named demo actors receive server-side role checks. Sessions are random 256-bit-class tokens stored as hashes, expire after eight hours, and use HttpOnly/SameSite=Strict cookies. Local HTTP cookies are not marked Secure; production must use TLS and external identity. The demo bootstrap password can sign in as each role and is not production separation of personnel.

Sensitive plate search and evidence require investigator/admin. Only the distinct approver actor can approve/revoke watchlists. Writes require a custom header and explicit local origin. Evidence retrieval validates relative keys and digests and uses restrictive SVG CSP. API errors avoid returning credentials or raw validation inputs. Use structured application logging without access logs containing query strings.

Do not expose the local console/API/database publicly. There is no owner lookup, face recognition, public plate search or external enforcement action. Recognition results and route anomalies are not proof of identity or wrongdoing. Production needs real identity/OIDC/MFA integration, rate limiting, TLS, retention/deletion policy, encrypted storage/backups, least-privileged database roles, audit export, session revocation policy and security review.

No security contact was supplied. Report issues privately to the repository owner through an established channel; do not include evidence or credentials in public issue trackers. No deployment credentials or third-party services are required.
