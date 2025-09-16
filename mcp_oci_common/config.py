import os
import oci

def get_oci_config(profile_name=None):
    profile = profile_name or os.getenv('OCI_PROFILE', 'DEFAULT')
    config = oci.config.from_file(profile_name=profile)
    config['region'] = os.getenv('OCI_REGION', config.get('region'))
    return config

def get_compartment_id():
    return os.getenv('COMPARTMENT_OCID')

def allow_mutations():
    return os.getenv('ALLOW_MUTATIONS', 'false').lower() == 'true'
