# Testing

## Direct OCI Integration Tests
This repository includes minimal integration tests that connect directly to OCI (no mocks). They are skipped by default and enabled explicitly via environment variables.

### Enable and Configure
Set the following environment variables, then run pytest (or use the Makefile target). If `TEST_OCI_REGION` or `TEST_OCI_TENANCY_OCID` are not set, the tests will read them from your OCI config (`~/.oci/config`) for the selected profile. Ensure `python3` is available on PATH, or provide values explicitly.
```
export OCI_INTEGRATION=1
export TEST_OCI_PROFILE=DEFAULT
export TEST_OCI_REGION=eu-frankfurt-1
export TEST_OCI_TENANCY_OCID=[Link to Secure Variable: OCI_TENANCY_OCID] # Your tenancy OCID
pytest -q
```
or
```
make test-integration
```

### What They Cover
- Doctor CLI connectivity (loads config and lists regions)
- IAM: list users (tenancy compartment)
- Object Storage: get namespace and list buckets (limit=1)
- Compute: list shapes (limit=1)
- Usage API: summarized costs over recent days

### Optional Tests
- Log Analytics run-query:
  - The test will try to auto-discover a namespace using the SDK (e.g., `list_namespaces`); if it cannot, set `TEST_LOGANALYTICS_NAMESPACE=<namespace_name>`
  - Executes a small stats query over the last hour
- Object Storage list-objects:
  - The test auto-discovers namespace and the first bucket (limit=1) in the tenancy; if none found, set `TEST_OCI_OS_BUCKET=<bucket_name>`

### Notes
- These tests perform read-only operations and should be safe for production tenancies.
- Ensure your profile has permissions for the called services.
- In CI, these tests remain skipped unless `OCI_INTEGRATION=1` and other variables are provided.
- Use `make integration-env` to print the required and optional variables.
 - You can also use the helper script which runs setup, detects tenancy and executes tests against Frankfurt:
```
./scripts/test_integration_frankfurt.sh
```
