import os
import oci
from oci.auth.signers import InstancePrincipalsSecurityTokenSigner

def get_oci_config(profile_name=None):
    profile = profile_name or os.getenv('OCI_PROFILE', 'DEFAULT')
    config_path = os.getenv('OCI_CONFIG_FILE', os.path.expanduser('~/.oci/config'))
    
    try:
        config = oci.config.from_file(file_location=config_path, profile_name=profile)
    except oci.exceptions.ConfigFileNotFound:
        try:
            # Fallback to instance principal
            signer = InstancePrincipalsSecurityTokenSigner()
            config = {'region': signer.region}
            config['signer'] = signer
        except Exception as e:
            raise RuntimeError(f"Failed to load OCI config and instance principal fallback: {str(e)}") from e
    
    config['region'] = os.getenv('OCI_REGION', config.get('region'))
    return config

def get_compartment_id():
    return os.getenv('COMPARTMENT_OCID')

def allow_mutations():
    return os.getenv('ALLOW_MUTATIONS', 'false').lower() == 'true'
