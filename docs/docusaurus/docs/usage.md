---
id: usage
title: Usage
---

Start a server via stdio:

```
mcp-oci-serve compute --profile DEFAULT --region eu-frankfurt-1
```

Call tools with the dev CLI:

```
mcp-oci list-tools objectstorage
mcp-oci call objectstorage oci_objectstorage_list_buckets --params '{"namespace_name":"<ns>","compartment_id":"ocid1.compartment..."}'
```

Next: [Development](development.md)

