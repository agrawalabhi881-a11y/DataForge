import logging
from typing import List

logger = logging.getLogger(__name__)

class LicenseChecker:
    """
    Validates dataset licenses to ensure compliance with commercial or research usage constraints.
    """

    # Permissive licenses safe for general model training & deployment
    PERMISSIVE_LICENSES = {
        "cc0-1.0", "mit", "apache-2.0", "cc-by-4.0", "odc-by-1.0", "public domain"
    }

    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self.logger = logging.getLogger(self.__class__.__name__)

    def is_license_compliant(self, license_name: str) -> bool:
        """
        Checks if a given license string falls under approved permissive guidelines.
        """
        if not license_name:
            self.logger.warning("No license specified for dataset. Compliance status: UNKNOWN")
            return not self.strict_mode

        normalized_license = license_name.strip().lower()
        
        is_safe = any(perm in normalized_license for perm in self.PERMISSIVE_LICENSES)
        
        if is_safe:
            self.logger.info(f"License '{license_name}' is compliant.")
            return True
        else:
            self.logger.warning(f"License '{license_name}' is restrictive or unrecognized.")
            return not self.strict_mode