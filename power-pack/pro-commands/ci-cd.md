---
description: Design a CI/CD pipeline from source to production
argument-hint: [describe the application and deployment target]
---
Design a CI/CD pipeline:

1. **Pipeline stages** — ordered stages from commit to production with purpose of each
2. **Build** — build steps, dependency caching, artifact output
3. **Test matrix** — unit, integration, e2e tests; parallelization; required vs. optional
4. **Security gates** — SAST, dependency scanning, secret detection, container scanning
5. **Artifact management** — what gets built, where it's stored, versioning/tagging scheme
6. **Deployment strategy** — blue/green, canary, rolling, or feature flags — with rollback procedure
7. **Environment progression** — dev → staging → production with promotion criteria
8. **Infrastructure as code** — Terraform/CloudFormation/Pulumi for the pipeline infrastructure itself
9. **Monitoring & alerts** — post-deploy health checks, error rate thresholds, automatic rollback triggers
10. **Pipeline as code** — complete GitHub Actions / GitLab CI / Jenkinsfile ready to use

Optimize for: fast feedback (fail early), safety (can always roll back), and developer experience.

Application: $ARGUMENTS
